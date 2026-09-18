"""Localhost HTTP API: transcript queue for the hooks + live dashboard."""

import json
import re
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from noisy_coding import credentials, diagnostics, harness, playback
from noisy_coding.config_dir import CONFIG_DIR
from noisy_coding.providers.config import ConfigurationError
from noisy_coding.listener import stt_lab
from noisy_coding.listener import pricing, speech, tab_audio
from noisy_coding.listener.dashboard import DASHBOARD_HTML
from noisy_coding.listener.state import ListenerState

_PRERELEASE_WORDS = {"a": "alpha", "b": "beta", "rc": "rc"}


def display_version(metadata_version: str) -> str:
    """Package metadata is PEP 440-normalised ("3.0.0a4"); the tag, the
    plugin manifest and the UI build all say "3.0.0-alpha.4". The badge
    compares strings, so the daemon must speak the same dialect (#100)."""
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(a|b|rc)(\d+)", metadata_version)
    if not match:
        return metadata_version
    base, word, number = match.groups()
    return f"{base}-{_PRERELEASE_WORDS[word]}.{number}"


try:
    from importlib.metadata import version as _pkg_version

    DAEMON_VERSION = display_version(_pkg_version("noisy-coding"))
except Exception:  # editable installs before metadata exists
    DAEMON_VERSION = "dev"

# Where releases are announced: the version field of the plugin manifest on
# main — updated by scripts/bump_version.py the moment a release lands.
LATEST_VERSION_URL = (
    "https://raw.githubusercontent.com/noisy/noisy-coding/main/.claude-plugin/plugin.json"
)
LATEST_CHECK_INTERVAL_SECONDS = 6 * 3600
_latest_checked_at = 0.0
_latest_check_lock = threading.Lock()


# #22: subagent speech reattachment. A speak call may claim a session id
# that owns no dashboard tab (a subagent/team session); the MCP server also
# sends the id the hooks registered for that directory. The rule: a subagent
# is not a conversation — it is a PARTICIPANT in one. Reattach the utterance
# to the registered conversation and tag it with a speaker so the UI can
# render it as its own persona.
#
# Each unknown session id gets a stable voice from this pool (hash-picked,
# never the parent's current voice), so a given subagent keeps one voice and
# one portrait for its whole life.
# One pool and one hash for everyone who gets a voice - see state.VOICE_POOL.
from noisy_coding.listener.state import VOICE_POOL as SUBAGENT_VOICE_POOL  # noqa: E402
from noisy_coding.listener.state import hash_pick as _hash_pick  # noqa: E402


def _subagent_voice(state: ListenerState, session_id: str, parent_voice: str) -> str:
    """A stable, unshared voice for a named speaker.

    The hash alone only guarantees stability; the claim ledger in state adds
    exclusivity, so two speakers never end up indistinguishable by ear.
    """
    pool = tuple(v for v in SUBAGENT_VOICE_POOL if v != parent_voice)
    return state.claim_voice(session_id, pool, _hash_pick)


def _resolve_speaker(
    state: ListenerState, body: dict
) -> tuple[str | None, str | None, str | None]:
    """(agent, speaker, voice_override) for an incoming /speak body.

    Two independent subagent signals compose here:
    - an explicit `speaker` name (a same-session subagent introducing
      itself, e.g. "researcher") — keeps the agent id, gains a persona;
    - a claimed id that owns no tab (a team/subagent SESSION) — reattached
      to `agent_fallback`; named by its `speaker` if sent, else by the
      voice persona it was dealt.
    """
    agent = str(body["agent"]) if body.get("agent") else None
    name = str(body.get("speaker") or "").strip() or None
    if agent and agent not in state.agents:
        fallback = str(body.get("agent_fallback") or "").strip() or None
        if fallback and fallback in state.agents:
            seed = name or agent
            voice = _subagent_voice(state, seed, state.character(fallback).get("voice", ""))
            return fallback, name or voice, voice
        # Neither id is known: register a visible tab instead of storing
        # speech no tab will ever show — bugs should be loud (#22). The
        # label is the FALLBACK form (short id) on purpose: this is often
        # just speak racing ahead of the hooks in a brand-new session, and
        # the hooks' later re-register with a real title must win. The
        # event row below stays as the loud part.
        state.register_agent(agent, label="New conversation")
        state.add_event("agent", f"unknown speaker '{agent[:8]}…' auto-registered")
        # A NAMED speaker keeps its persona voice even on this emergency
        # path - otherwise every viewer collapses onto the agent's default
        # voice in the window right after a daemon restart (handoff OPEN 1).
        voice = (
            _subagent_voice(state, name, state.character(agent).get("voice", ""))
            if name
            else None
        )
        return agent, name, voice
    if name:
        voice = _subagent_voice(state, name, state.character(agent).get("voice", ""))
        return agent, name, voice
    return agent, None, None


def _maybe_refresh_latest_version(state: ListenerState) -> None:
    """Kick a background fetch of the newest release version, rate-limited.

    Piggybacks on /status polls: cheap check of a timestamp, and the actual
    network call runs in a daemon thread so a slow GitHub never delays the
    dashboard. Failures are silent — the badge just keeps the last answer.
    """
    global _latest_checked_at
    with _latest_check_lock:
        if time.time() - _latest_checked_at < LATEST_CHECK_INTERVAL_SECONDS:
            return
        _latest_checked_at = time.time()

    def fetch() -> None:
        try:
            import urllib.request

            with urllib.request.urlopen(LATEST_VERSION_URL, timeout=10) as response:
                version = json.load(response).get("version")
            if isinstance(version, str) and version:
                state.set_latest_version(version)
        except Exception:
            pass

    threading.Thread(target=fetch, daemon=True).start()


DEFAULT_PORT = 8765
# Bind address. Loopback by default; a Docker container must bind 0.0.0.0
# or the published port can't reach it (set NOISY_CODING_BIND=0.0.0.0 there).
BIND_ENV_VAR = "NOISY_CODING_BIND"
# Mic-level frame cadence for the dashboard oscilloscope (~20 fps). A data
# rate for smooth rendering, not coordination logic.
MIC_STREAM_INTERVAL_SECONDS = 0.05
# The built Vue HUD (dashboard/dist) served at /next; legacy stays at /.
def _dist_dir() -> Path:
    """Where the built dashboard lives.

    Frozen (PyInstaller) the source tree is gone: files bundled by the spec
    are unpacked next to the executable, under sys._MEIPASS. From a checkout
    they sit three levels up, in dashboard/dist. Getting this wrong shows
    "HUD not built yet" from a daemon that is otherwise perfectly healthy.
    """
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled) / "dashboard" / "dist"
    return Path(__file__).resolve().parents[3] / "dashboard" / "dist"


DIST_DIR = _dist_dir()
STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".map": "application/json",
}
BUILD_HINT_HTML = """<!doctype html><meta charset="utf-8">
<body style="font-family:monospace;background:#02060c;color:#cfeaf6;padding:40px">
<h2>HUD not built yet</h2>
<p>Run: <code>cd dashboard &amp;&amp; npm install &amp;&amp; npm run build</code>, then reload.</p>
</body>"""
PORT_ENV_VAR = "NOISY_CODING_LISTENER_PORT"
CHARACTER_FILE = CONFIG_DIR / "character.json"
VOICE_CLAIMS_FILE = CONFIG_DIR / "voice-claims.json"
SPEAKER_COLORS_FILE = CONFIG_DIR / "speaker-colors.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


# Grok voice genders (matches the dashboard's voice list). The agent's
# Polish grammar must agree with the voice it speaks with.
FEMALE_VOICES = {"ara", "aurora", "carina", "celeste", "eve", "iris", "liora", "luna", "ursa"}


def _voice_gender(voice: str) -> str:
    return "female" if voice in FEMALE_VOICES else "male"


def notify_gender_change(
    state: ListenerState, agent: str | None, old_voice: str, new_voice: str
) -> None:
    """Tell the agent to switch grammatical gender — silently.

    Sent only when the voice's gender actually flips, and phrased so the
    agent applies it without ever commenting on it.
    """
    if _voice_gender(old_voice) == _voice_gender(new_voice):
        return
    if agent not in (None, state.active_agent):
        return
    gender = _voice_gender(new_voice)
    forms = "feminine (e.g. „zrobiłam”)" if gender == "female" else "masculine (e.g. „zrobiłem”)"
    state.add_transcript(
        f"[PERSONA] Your voice is now {gender}. From this point on, speak and write "
        f"in the first person using {forms} grammatical forms in Polish. Apply this "
        "silently: never mention, comment on, or acknowledge the voice change or "
        "this note — just continue whatever is pending as if it did not exist."
    )


def list_input_devices() -> list:
    """Fresh input-device list via a subprocess.

    A new PortAudio instance sees devices plugged in after the daemon
    started; the daemon's own (cached) instance would not — and it cannot
    be re-initialized while the input stream is running.
    """
    try:
        result = subprocess.run(_device_probe_command(), capture_output=True, timeout=10)
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


DEVICE_PROBE_SCRIPT = (
    "import json, sounddevice as sd; devices = sd.query_devices(); "
    "default_in = sd.default.device[0]; "
    "print(json.dumps([{'name': d['name'], 'default': i == default_in} "
    "for i, d in enumerate(devices) if d['max_input_channels'] > 0]))"
)


def _device_probe_command() -> list[str]:
    """In a PyInstaller build sys.executable is the frozen daemon itself, which
    ignores `-c` and would boot a SECOND engine (same port, open mic, killed
    by the timeout) on every /devices call. The frozen binary answers
    `--list-devices` instead; a source checkout runs the script inline."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--list-devices"]
    return [sys.executable, "-c", DEVICE_PROBE_SCRIPT]


def save_characters(state: ListenerState) -> None:
    """Persist per-agent characters so voice choices survive restarts."""
    try:
        CHARACTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        CHARACTER_FILE.write_text(json.dumps(state.all_characters()))
    except OSError:
        pass


def save_speaker_colors(state: ListenerState) -> None:
    try:
        SPEAKER_COLORS_FILE.write_text(json.dumps(
            {"colors": state.speaker_colors(), "labels": state.speaker_labels()}
        ))
    except OSError:
        pass


def load_speaker_colors(state: ListenerState) -> None:
    try:
        state.load_speaker_styles(json.loads(SPEAKER_COLORS_FILE.read_text()))
    except (OSError, ValueError):
        pass


def save_voice_claims(state: ListenerState) -> None:
    """Persist the claim ledger - a voice a viewer earned outlives a restart."""
    try:
        VOICE_CLAIMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        VOICE_CLAIMS_FILE.write_text(json.dumps(state.voice_claims()))
    except OSError:
        pass


INTRO_FLAG = CONFIG_DIR / "intro-done"


def _queue_first_contact_intro(state: ListenerState) -> None:
    """First contact just completed — have Claude say hello.

    The user is looking at the dashboard and the tab can already play
    (pasting the key was the browser's autoplay gesture; the WS lease
    needs no permission). The greeting rides the normal transcript queue
    with a [DASHBOARD] prefix — a daemon event, not the user's speech —
    and fires once per install (flag file survives restarts).
    """
    if INTRO_FLAG.exists():
        return
    state.add_transcript(
        "[DASHBOARD] The user just finished first-contact setup and is "
        "looking at the dashboard. Introduce yourself aloud with the "
        "speak tool — welcome them to Noisy Studio in one or two warm "
        "sentences and ask them to click the amber ENABLE TAB AUDIO "
        "banner so this tab can also become their microphone."
    )
    try:
        INTRO_FLAG.parent.mkdir(parents=True, exist_ok=True)
        INTRO_FLAG.touch()
    except OSError:
        pass


def _hotkeys_snapshot(state: ListenerState) -> dict:
    listener = getattr(state, "hotkey_listener", None)
    base = (
        listener.snapshot()
        if listener is not None
        else {"configured": False, "permission": "unknown", "armed": False, "bindings": {}, "problems": {}}
    )
    base["stored"] = state.hotkeys  # every chord the user set, armed or not
    return base


def _apply_hotkeys(state: ListenerState, patch: dict[str, str]) -> tuple[dict, dict]:
    """Merge a hotkey patch (#104). A chord that would collide with another
    action, or cannot be parsed, is NOT stored - the user sees the problem
    next to the field and the previous binding survives. System-shortcut
    warnings are stored and reported. Rearms the tap; a user pick is the
    one moment macOS may prompt for Input Monitoring (#97)."""
    from noisy_coding.listener import hotkey as hotkey_mod
    from noisy_coding.listener.chords import problems

    known = {a: str(t or "") for a, t in patch.items() if a in hotkey_mod.ACTIONS}
    current = state.hotkeys
    proposed = {**current, **known}
    found = problems({a: t for a, t in proposed.items() if t})
    rejected = {}
    for action in known:
        kind = found.get(action, {}).get("kind")
        if kind in ("collision", "invalid"):
            rejected[action] = found[action]
            proposed[action] = current.get(action, "")  # keep what was there
    stored = state.set_hotkeys(proposed)
    listener = getattr(state, "hotkey_listener", None)
    if listener is not None:
        listener.configure_bindings(stored, may_prompt=True)
    reported = {**problems({a: t for a, t in stored.items() if t}), **rejected}
    return stored, reported


def save_settings(state: ListenerState) -> None:
    """Persist tuning that must survive daemon restarts."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(
                {
                    "end_silence_ms": state.end_silence_ms,
                    "mic_sensitivity": state.mic_sensitivity,
                    "smart_turn": state.smart_turn,
                    "mode": state.mode,
                    "tts_mode": state.tts_mode,
                    "smart_turn_mode": state.smart_turn_mode,
                    "detection_mode": state.detection_mode,
                    "ptt_hold_key": state.ptt_hold_key,
                    "ptt_toggle_key": state.ptt_toggle_key,
                    "ptt_cancel_key": state.ptt_cancel_key,
                    "hotkeys": state.hotkeys,
                    "input_device": state.input_device,
                    "output_device": state.output_device,
                    "language": state.language,
                    # The user's conscious pick — a restart must not re-run
                    # the first-to-register race and reroute their speech.
                    "active_agent": state.active_agent,
                }
            )
        )
    except OSError:
        pass


_ADAPTERS: dict[str, harness.Harness] = {}


def _adapter(name: str) -> harness.Harness:
    if name not in _ADAPTERS:
        _ADAPTERS[name] = harness.get(name)
    return _ADAPTERS[name]


def _apply_harness_event(
    state: ListenerState, name: str, payload: dict, listen_seconds: float | None = None
) -> dict:
    """Run one hook payload through its harness adapter and the registry.

    The registry is the source of truth for tabs; the legacy agent table in
    ListenerState is kept in step (same key) so speech routing, activity and
    the dashboard keep working while they migrate to /status.conversations.
    """
    adapter = _adapter(name)
    result = adapter.interpret(payload)
    registry = state.conversations
    conversation = registry.apply(name, result, adapter.capabilities)
    key = conversation.key
    if conversation.hidden:
        # The user closed this tab. Routine hooks from a still-running
        # session must not resurrect it; only a new session or a new user
        # turn does (registry.apply un-hides on those). Identity and drain
        # rules still apply - closing a tab does not change who speaks.
        return {
            "conversation": key,
            "may_drain": result.may_drain,
            "speech_identity": result.speech_identity,
            "listener": "none",
            "participant": result.participant,
            "label": conversation.label(),
        }
    already = key in state.agents
    state.register_agent(key, conversation.label())
    if not already:
        state.add_event("agent", f"'{conversation.label()}' registered ({adapter.label})")
    for event in result.events:
        if event.kind == "activity" and event.participant is None:
            state.set_activity(key, event.detail)
        elif event.kind == "turn_ended":
            state.set_activity(key, "")
        elif event.kind == "title_changed" and event.title:
            state.register_agent(key, event.title)
    response = {
        "conversation": key,
        "may_drain": result.may_drain,
        "speech_identity": result.speech_identity,
        "listener": result.listener,
        "participant": result.participant,
        "label": conversation.label(),
    }
    if result.listener in ("start", "poll"):
        window = adapter.capabilities.max_idle_seconds
        if listen_seconds is not None and window:
            # The hook may shorten (never lengthen) the harness window - a
            # Codex user picks how long the synchronous Stop holds the turn.
            window = max(0.0, min(float(listen_seconds), window))
        if window is not None and window <= 0:
            response["listener"] = "none"  # idle listening disabled by the hook
        else:
            response["listener_id"] = registry.listener_started(key, window=window)
            response["listen_seconds"] = window
            response["harness"] = name
    return response


def _render_for(state: ListenerState, key: str, messages: list[str], moment: str) -> dict | None:
    conversation = state.conversations.get(key)
    if conversation is None:
        return None
    try:
        adapter = _adapter(conversation.harness)
    except KeyError:
        return None
    delivery = adapter.deliver(messages, moment)  # type: ignore[arg-type]
    return {
        "context": delivery.context,
        "system_message": delivery.system_message,
        "exit_code": delivery.exit_code,
    }


def _render_delivery(state: ListenerState, key: str, transcripts: list[dict], moment: str) -> dict | None:
    if not transcripts:
        return None
    return _render_for(state, key, [t["text"] for t in transcripts], moment)


def _named_agent_labels(state: ListenerState) -> dict:
    """agent -> label, with the registry's name for every conversation it
    knows. The legacy table falls back to the raw agent string (an id, or
    for Claude a transcript path) when it has no label; that must never
    reach the screen."""
    labels = state.agent_labels
    for name in list(labels):
        conversation = state.conversations.get(name)
        if conversation is not None:
            labels[name] = conversation.label()
        elif labels[name] == name:
            labels[name] = "New conversation"
    return labels


def _stable_agents_meta(state: ListenerState) -> dict:
    """Tab metadata driven by the conversation registry, not by heartbeats.

    `online` used to mean "heartbeat within 180 s", which made a tab flip
    grey mid-think, hid the close button for three minutes after every
    daemon restart (each tab re-registered with a fresh heartbeat), and
    reshuffled the strip depending on who polled first. The registry knows
    the truth from lifecycle events: a conversation is alive until its
    session ends, its arrival is when it was created, and its order is its
    position. Tabs the registry does not know keep the legacy shape.
    """
    meta = state.agents_meta
    for name, entry in meta.items():
        conversation = state.conversations.get(name)
        if conversation is None:
            continue
        status = state.conversations.status(name)
        entry["label"] = conversation.label()  # a name, never an id or a path
        # The strip's order is the registry's persisted position (which
        # drag-and-drop updates), so it is identical before and after a
        # restart. The in-memory manual_pos table did not survive one.
        entry["manual_pos"] = conversation.position
        entry["online"] = status != "ended"
        entry["status"] = status
        entry["activated_at"] = conversation.created_at
        entry["offline_since"] = conversation.last_event_at if status == "ended" else None
    return meta


def _revive_if_known(state: ListenerState, presented: str) -> str:
    """Resolve an id to its conversation and bring a closed tab back properly.

    A closed (hidden) conversation whose session then speaks, reports
    activity or registers must reappear as ITSELF - same key, same title -
    not as a fresh hash-labelled tab conjured by the legacy auto-register.
    Returns the key to use (the presented id when the registry does not
    know it).
    """
    key = state.conversations.resolve(presented) or presented
    conversation = state.conversations.get(key)
    if conversation is None:
        return key
    if conversation.hidden or key not in state.agents:
        state.conversations.unhide(key)
        state.register_agent(key, conversation.label())
        state.add_event("agent", f"'{conversation.label()}' is back (its session spoke)")
    return key


def status_payload(state: ListenerState) -> dict:
    """The daemon's full state as the dashboard sees it - ONE builder for
    GET /status and for the WebSocket state stream, so both surfaces can
    never disagree about what the daemon means."""
    _maybe_refresh_latest_version(state)
    from noisy_coding import providers as _providers
    from noisy_coding.providers import selection

    return {
                            "listening": not state.paused,
                            "muted": state.user_muted,
                            "voice_muted": state.voice_muted,
                            "api_key_set": bool(credentials.api_key()),
                            # The gate's real question: is a READY engine
                            # selected both ways? (A local-only setup is
                            # configured with no key at all.) Additive key.
                            "voice_ready": _providers.voice_ready(),
                            "voice_labels": selection.active_voice_labels(),
                            "recognition_mode": _providers.effective_mode("stt", state.mode),
                            "recognition_live_available": _providers.effective_mode("stt", "live") == "live",
                            **speech.output_status(state),
                            # Named speakers whose bubbles carry a platform
                            # tint (twitch purple / youtube red).
                            "speaker_colors": state.speaker_colors(),
                            "speaker_labels": state.speaker_labels(),
                            "api_key_hint": credentials.api_key_hint(),
                            "recording": state.recording,
                            "claude_speaking": state.claude_speaking,
                            "playing_utterance_id": state.playing_utterance_id,
                            "stt_latency_ms": state.latency_ms["stt"],
                            "tts_latency_ms": state.latency_ms["tts"],
                            "speaking_agents": state.speaking_agents,
                            "queued": state.queued_count,
                            "last_transcript_at": state.last_transcript_at,
                            "session_cost_usd": state.session_cost_usd,
                            "usage": state.usage,
                            "credits_usd": state.credits_usd,
                            "mode": state.mode,
                            "tts_mode": state.tts_mode,
                            "end_silence_ms": state.end_silence_ms,
                            "mic_sensitivity": state.mic_sensitivity,
                            "smart_turn": state.smart_turn,
                            "smart_turn_mode": state.smart_turn_mode,
                            "detection_mode": state.detection_mode,
                            "ptt_hold_key": state.ptt_hold_key,
                            "ptt_toggle_key": state.ptt_toggle_key,
                            "ptt_cancel_key": state.ptt_cancel_key,
                            "shutdown_at": state.shutdown_at,
                            "ptt_held": state.ptt_held,
                            "input_device": state.input_device,
                            # What is actually open right now; differs from
                            # input_device while the pick is unavailable (#41).
                            "active_input_device": state.active_input_device,
                            "output_device": state.output_device,
                            "browser_audio": state.browser_audio,
                            "hotkeys": _hotkeys_snapshot(state),
                            "tab_audio": state.tab_audio_alive,
                            "activity": state.activity,
                            "nudge_clocks": state.nudge_clocks(),
                            "language": state.language,
                            "diagnostic_checks": state.diagnostic_checks,
                            "agents": state.agents,
                            "agent_labels": _named_agent_labels(state),
                            "agents_meta": _stable_agents_meta(state),
                            # Each conversation's voice, so a client can draw its
                            # portrait without asking /character once per agent.
                            "agent_voices": {
                                name: state.character(name).get("voice", "")
                                for name in state.agents
                            },
                            "queued_by_agent": state.queued_by_agent,
                            "muted_agents": state.muted_agents,
                            "version": DAEMON_VERSION,
                            "latest_version": state.latest_version,
                            "active_agent": state.active_agent,
                            # The harness-contract view of the tabs (keys,
                            # aliases, live/idle/deaf/ended, listening_until).
                            "conversations": state.conversations.snapshot(),
                        }


def state_snapshot(state: ListenerState) -> dict:
    """Everything the dashboard renders, in one message: status plus every
    utterance. Pushed over the state stream whenever it changes."""
    return {"type": "snapshot", "status": status_payload(state), "utterances": state.utterances()}


def _handler_class(state: ListenerState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                self._handle_GET()
            except ConfigurationError as error:
                self._respond({"error": str(error), "code": "invalid_speech_settings"}, status=409)

        def _handle_GET(self) -> None:
            url = urlparse(self.path)
            if url.path == "/":
                # The Vue HUD is the main dashboard; the legacy one stays
                # at /legacy (and serves as fallback before the first build).
                if DIST_DIR.is_dir():
                    self._serve_hud_file("index.html")
                else:
                    self._respond_html(DASHBOARD_HTML)
            elif url.path == "/legacy":
                self._respond_html(DASHBOARD_HTML)
            elif url.path == "/debug" or url.path == "/logs":
                # SPA sandboxes — same bundle, routed client-side. /debug is
                # the chat-window state sandbox; /logs streams the event log
                # (incl. #16 nudge decisions) for a screen the user can watch.
                self._serve_hud_file("index.html")
            elif url.path.startswith("/assets/") or (
                "/" not in url.path[1:]
                and Path(url.path).suffix in STATIC_CONTENT_TYPES
            ):
                # Root-level static files (favicons, the avatars sprite, and
                # whatever public/ grows next) — extension-allowlisted, and
                # _serve_hud_file guards against path traversal.
                self._serve_hud_file(url.path[1:])
            elif url.path == "/drain":
                query = parse_qs(url.query)
                agent = query.get("conversation", query.get("agent", [None]))[0]
                listener_id = query.get("listener", [None])[0]
                if agent:
                    agent = state.conversations.resolve(agent) or agent
                if listener_id and not state.conversations.listener_alive(agent or "", listener_id):
                    # A newer listener took over (or this one expired):
                    # stand down without touching the queue, so the current
                    # listener - not a stale one - receives the message.
                    self._respond({"transcripts": [], "nudge": None, "stand_down": True})
                    return
                active_before = state.active_agent
                conversation = state.conversations.get(agent or "")
                hidden = bool(conversation and conversation.hidden)
                transcripts = [asdict(t) for t in state.drain(agent, touch=not hidden)]
                if state.active_agent != active_before:
                    save_settings(state)  # bootstrap activation must stick too
                # Narration nudge (#16): piggybacks on the poll the hooks
                # already make — the daemon lends the clockless model a
                # sense of elapsed silence. Old hooks ignore the extra key.
                nudge = state.pop_due_nudge(agent) if agent else None
                moment = "wake" if listener_id else "mid_turn"
                delivery = _render_delivery(state, agent or "", transcripts, moment)
                self._respond({
                    "transcripts": transcripts,
                    "nudge": nudge,
                    "stand_down": False,
                    "delivery": delivery,
                })
            elif url.path == "/events":
                since = int(parse_qs(url.query).get("since", ["0"])[0])
                self._respond({"events": state.events_since(since)})
            elif url.path == "/diagnose":
                # The same per-check breakdown /credentials runs at save
                # time, on demand — mid-session failures become
                # self-diagnosable without hand-crafted curl calls.
                if not credentials.api_key():
                    self._respond({"error": "no API key configured"}, status=400)
                else:
                    self._respond(
                        {"checks": diagnostics.run_checks_sync(state.set_diagnostic_checks)}
                    )
            elif url.path == "/utterances":
                agent = parse_qs(url.query).get("agent", [None])[0]
                self._respond({"utterances": state.utterances(agent)})
            elif url.path == "/character":
                agent = parse_qs(url.query).get("agent", [None])[0]
                self._respond({"character": state.character(agent)})
            elif url.path == "/devices":
                # The dashboard tab is a virtual microphone: selectable
                # always, audible only while a tab holds the audio lease.
                browser_entry = (
                    [{"name": "THIS BROWSER TAB", "default": False, "value": "browser"}]
                    if state.browser_audio
                    else []
                )
                self._respond(
                    {
                        "devices": list_input_devices() + browser_entry,
                        "selected": state.input_device,
                    }
                )
            elif url.path == "/speech-settings":
                from noisy_coding.providers import selection
                identities = sorted({c['voice'] for c in state.all_characters().values()} |
                                    set(state.voice_claims().values()) | {state.character()['voice']})
                self._respond(selection.snapshot(identities, state.language))
            elif url.path == "/providers":
                # Voice engines: the full catalog (setup metadata per
                # provider) plus what is active per direction — the
                # dashboard renders fields it has never heard of, so a
                # new provider never means new frontend code.
                from noisy_coding import providers
                from noisy_coding.providers import config as provider_config
                from noisy_coding.providers import local as local_provider

                self._respond(
                    {
                        "catalog": providers.catalog(),
                        "active": {
                            "tts": provider_config.tts_provider_name(),
                            "stt": provider_config.stt_provider_name(),
                        },
                        # Local model weights: what's on disk, what's
                        # arriving right now (the UI polls while any
                        # entry says "downloading" and draws a bar).
                        "downloads": local_provider.download_status(),
                    }
                )
            elif url.path == "/stream/mic":
                self._stream_mic_levels()
            elif url.path == "/tests/speech":
                self._respond(stt_lab.list_tests())
            elif url.path == "/stt-lab":
                # The lab grew into the status page's speech section.
                self.send_response(302)
                self.send_header("Location", "/next/status")
                self.end_headers()
            elif url.path == "/next":
                self.send_response(301)
                self.send_header("Location", "/next/")
                self.end_headers()
            elif url.path.startswith("/next/"):
                self._serve_hud_file(url.path[len("/next/"):] or "index.html")
            elif url.path == "/status":
                self._respond(status_payload(state))
            else:
                self._respond({"error": "not found"}, status=404)

        def do_POST(self) -> None:
            try:
                self._handle_POST()
            except ConfigurationError as error:
                self._respond({"error": str(error), "code": "invalid_speech_settings"}, status=409)

        def _handle_POST(self) -> None:
            if self.path == "/harness/event":
                body = self._read_json_body()
                name = str(body.get("harness") or "")
                payload = body.get("payload")
                if name not in harness.names() or not isinstance(payload, dict):
                    self._respond({"error": "harness and payload required"}, status=400)
                    return
                active_before = state.active_agent
                listen = body.get("listen_seconds")
                try:
                    response = _apply_harness_event(
                        state, name, payload,
                        float(listen) if isinstance(listen, (int, float)) else None,
                    )
                except harness.HarnessError as error:
                    state.add_event("voice_identity_error", str(error))
                    self._respond({"error": str(error)}, status=422)
                    return
                if state.active_agent != active_before:
                    save_settings(state)
                self._respond(response)
            elif self.path == "/harness/render":
                body = self._read_json_body()
                key = state.conversations.resolve(str(body.get("conversation") or "")) or ""
                messages = [str(m) for m in body.get("messages") or [] if str(m).strip()]
                moment = "wake" if body.get("moment") == "wake" else "mid_turn"
                rendered = _render_for(state, key, messages, moment) if key and messages else None
                if rendered is None:
                    self._respond({"error": "unknown conversation or no messages"}, status=404)
                else:
                    self._respond(rendered)
            elif self.path == "/harness/listener":
                body = self._read_json_body()
                key = state.conversations.resolve(str(body.get("conversation") or "")) or ""
                listener_id = str(body.get("listener_id") or "")
                if not key or not listener_id:
                    self._respond({"error": "conversation and listener_id required"}, status=400)
                    return
                reason = str(body.get("reason") or "")
                state.conversations.listener_stopped(key, listener_id, reason)
                if reason == "timeout":
                    label = state.agent_labels.get(key, key[-8:])
                    state.add_event("deaf", f"'{label}' stopped listening ({reason})")
                self._respond({"ok": True, "status": state.conversations.status(key)})
            elif self.path == "/register":
                body = self._read_json_body()
                name = str(body.get("name", "")).strip()
                name = state.conversations.resolve(name) or name
                label = str(body.get("label", "")).strip()
                known = state.conversations.get(name)
                if known is not None and known.hidden:
                    # The user closed this tab. Sessions on the old hook
                    # scripts re-register on every tool call; that must not
                    # bring the tab back. Keep its name current, stay hidden.
                    state.conversations.adopt(name, label, unhide=False)
                    self._respond({"registered": name, "active_agent": state.active_agent, "hidden": True})
                    return
                if name:
                    already = name in state.agents
                    active_before = state.active_agent
                    # Old hook scripts register here directly, bypassing the
                    # harness contract. Adopt the conversation into the
                    # registry so it is persisted and its rename is kept -
                    # otherwise these tabs vanished on every daemon restart.
                    state.conversations.adopt(name, label)
                    state.register_agent(name, label)
                    if not already:  # avoid spamming the event log every hook fire
                        state.add_event("agent", f"'{label or name}' registered")
                    if state.active_agent != active_before:
                        save_settings(state)  # bootstrap activation must stick too
                    self._respond(
                        {"registered": name, "active_agent": state.active_agent}
                    )
                else:
                    self._respond({"error": "name required"}, status=400)
            elif self.path == "/dismiss-agent":
                name = str(self._read_json_body().get("name", "")).strip()
                name = state.conversations.resolve(name) or name
                if name not in state.agents:
                    self._respond({"error": "unknown agent"}, status=404)
                    return
                handed_to = None
                if name == state.active_agent:
                    # Closing the mic's tab hands the mic to the next visible
                    # conversation (browser-tab semantics), loudly - the user
                    # must know where their speech goes now.
                    remaining = [k for k in state.conversations.visible_keys()
                                 if k != name and k in state.agents]
                    handed_to = remaining[0] if remaining else None
                    state.set_active_agent(handed_to) if handed_to else state.clear_active_agent()
                    state.add_event("agent", f"mic handed to '{handed_to}'" if handed_to else "mic released - no conversation active")
                    save_settings(state)
                # Hidden, not forgotten: the conversation stays in the registry
                # and comes back when the user talks there again.
                state.dismiss_agent(name, force=True)
                state.conversations.hide(name)
                state.add_event("agent", f"'{name}' closed")
                self._respond({"dismissed": name, "active_agent": state.active_agent})
            elif self.path == "/hotkeys/permission":
                # The settings GRANT button (#97): request Input Monitoring now
                # and arm the configured keys if macOS says yes.
                listener = getattr(state, "hotkey_listener", None)
                self._respond(listener.request_permission() if listener is not None else {})
            elif self.path == "/mute-agent":
                body = self._read_json_body()
                name = str(body.get("agent", "")).strip()
                if name:
                    muted = state.set_agent_muted(name, bool(body.get("muted", True)))
                    if name in muted and state.interrupt_playing_as_unheard(
                        "conversation muted", agent=name
                    ):
                        # Muting THIS conversation while its clip plays:
                        # instant silence, the clip parks unheard.
                        playback.stop_all_players()
                        live_bridge = tab_audio.bridge()
                        if live_bridge is not None:
                            live_bridge.stop_tab_playback()
                    state.add_event("agent", f"'{name}' {'muted' if name in muted else 'unmuted'}")
                    self._respond({"muted_agents": muted})
                else:
                    self._respond({"error": "agent required"}, status=400)
            elif self.path == "/reorder-agents":
                order = self._read_json_body().get("order")
                if isinstance(order, list):
                    state.reorder_agents([str(n) for n in order])
                    state.conversations.reorder([str(n) for n in order])
                    self._respond({"reordered": True})
                else:
                    self._respond({"error": "order must be a list"}, status=400)
            elif self.path == "/active-agent":
                name = str(self._read_json_body().get("name", "")).strip()
                name = state.conversations.resolve(name) or name
                active = state.set_active_agent(name)
                state.add_event("agent", f"switched to '{active}'")
                save_settings(state)
                self._respond({"active_agent": active})
            elif self.path == "/pause":
                state.set_paused(True)
                state.add_event("muted")
                self._respond({"listening": False})
            elif self.path == "/resume":
                state.set_paused(False)
                state.add_event("unmuted")
                self._respond({"listening": True})
            elif self.path == "/tests/speech/run":
                # One recording, one pipeline, one transcription - small on
                # purpose: the page fires these in PARALLEL and each row
                # fills in as its request lands.
                self._respond(stt_lab.run_one(self._read_json_body()))
            elif self.path == "/tests/speech/bless":
                body = self._read_json_body()
                if stt_lab.bless(str(body.get("file","")), str(body.get("text",""))):
                    self._respond({"ok": True})
                else:
                    self._respond({"error": "file and non-empty text required"}, status=400)
            elif self.path in ("/speaker-color", "/speaker-style"):
                body = self._read_json_body()
                speaker = str(body.get("speaker", ""))
                color = str(body["color"]) if "color" in body else None
                label = str(body["label"]) if "label" in body else None
                if state.set_speaker_style(speaker, color=color, label=label):
                    save_speaker_colors(state)
                    self._respond({"ok": True, "speaker": speaker,
                                   "color": color, "label": label})
                else:
                    self._respond(
                        {"error": "speaker required; color, if given, one of "
                         + "/".join(state.SPEAKER_PALETTE)},
                        status=400,
                    )
            elif self.path == "/character":
                body = self._read_json_body()
                agent = body.get("agent")  # which tab's character (None=active)
                before = state.character(agent)
                values = state.set_character(body, agent)
                traits = ", ".join(
                    f"{k} {v}/100"
                    for k, v in values.items()
                    if k not in ("voice", "speed")
                )
                summary = (
                    f"{traits}, voice '{values['voice']}', speed {values['speed']}x"
                )
                state.add_event("character", summary)
                # The agent is told ONLY about trait changes (they shape its
                # style, a brief in-character ack is welcome). Voice and
                # speed are the daemon's business — switching them must
                # never provoke a comment from Claude.
                traits_changed = any(
                    before.get(k) != values.get(k)
                    for k in values
                    if k not in ("voice", "speed")
                )
                # The instruction reaches the agent via its queue only if it's
                # the active one; editing a background tab just stores the values.
                if traits_changed and agent in (None, state.active_agent):
                    state.add_transcript(
                        f"[CHARACTER] The user moved your character sliders to: {summary}. "
                        "Adjust the style of your spoken and written replies accordingly "
                        "— the daemon applies the voice and speed to your speech by "
                        "itself — and briefly acknowledge the new setting in character. "
                        "Never comment on the voice or speed."
                    )
                notify_gender_change(state, agent, before["voice"], values["voice"])
                save_characters(state)
                self._respond({"character": values})
            elif self.path == "/voice":
                # Claude's deliberate voice switch (the change_voice tool):
                # updates this agent's character, so the dashboard shows it
                # and every later speak uses it. Speak itself carries no
                # voice information.
                body = self._read_json_body()
                voice = str(body.get("voice_id", "")).strip().lower()
                speaker = str(body.get("speaker") or "").strip()
                if not voice.isalpha():
                    self._respond({"error": "voice_id must be a voice name"}, status=400)
                elif speaker:
                    # Moving a named speaker's voice, not the agent's own.
                    # The ledger arbitrates: first come, first served.
                    outcome = state.set_voice_claim(speaker, voice, SUBAGENT_VOICE_POOL)
                    if outcome == "ok":
                        save_voice_claims(state)
                        state.add_event("voice", f"'{speaker}' now speaks as '{voice}'")
                        self._respond({"voice": voice, "speaker": speaker})
                    elif outcome == "taken":
                        holder = next(
                            (n for n, v in state.voice_claims().items() if v == voice), ""
                        )
                        self._respond(
                            {"error": f"'{voice}' is already taken", "held_by": holder},
                            status=409,
                        )
                    else:
                        self._respond({"error": f"no such voice '{voice}'"}, status=400)
                else:
                    agent = str(body["agent"]) if body.get("agent") else None
                    before_voice = state.character(agent)["voice"]
                    values = state.set_character({"voice": voice}, agent)
                    state.add_event("voice", f"Claude switched voice to '{values['voice']}'")
                    notify_gender_change(state, agent, before_voice, values["voice"])
                    save_characters(state)
                    self._respond({"voice": values["voice"]})
            elif self.path == "/settings":
                body = self._read_json_body()
                result = {}
                if "end_silence_ms" in body:
                    result["end_silence_ms"] = state.set_end_silence_ms(
                        body["end_silence_ms"]
                    )
                if "mic_sensitivity" in body:
                    result["mic_sensitivity"] = state.set_mic_sensitivity(
                        body["mic_sensitivity"]
                    )
                if "smart_turn" in body:
                    result["smart_turn"] = state.set_smart_turn(body["smart_turn"])
                if body.get("tts_mode") in ("batch", "live"):
                    state.set_tts_mode(body["tts_mode"])
                    result["tts_mode"] = body["tts_mode"]
                legacy = {"ptt_hold_key": "hold", "ptt_toggle_key": "toggle", "ptt_cancel_key": "scratch"}
                if "hotkeys" in body or any(k in body for k in legacy):
                    # {action: chord text}; the legacy three keys map onto it.
                    patch = {legacy[k]: body[k] for k in legacy if isinstance(body.get(k), str)}
                    if isinstance(body.get("hotkeys"), dict):
                        patch.update({str(a): str(t or "") for a, t in body["hotkeys"].items()})
                    result["hotkeys"], result["hotkey_problems"] = _apply_hotkeys(state, patch)
                    result["ptt_hold_key"] = state.ptt_hold_key
                    result["ptt_toggle_key"] = state.ptt_toggle_key
                    result["ptt_cancel_key"] = state.ptt_cancel_key
                if body.get("smart_turn_mode") in ("soft", "hard"):
                    result["smart_turn_mode"] = state.set_smart_turn_mode(
                        body["smart_turn_mode"]
                    )
                if body.get("detection_mode") in ("auto", "ptt"):
                    result["detection_mode"] = state.set_detection_mode(
                        body["detection_mode"]
                    )
                    if result["detection_mode"] == "auto":
                        state.release_ptt()  # leaving PTT never leaves a stale hold
                if "language" in body:
                    result["language"] = state.set_language(str(body["language"]))
                if "input_device" in body:
                    result["input_device"] = state.set_input_device(str(body["input_device"]))
                if "output_device" in body:
                    result["output_device"] = state.set_output_device(str(body["output_device"]))
                if result:
                    save_settings(state)
                    self._respond(result)
                else:
                    self._respond({"error": "no known setting in body"}, status=400)
            elif self.path == "/speech-settings":
                from noisy_coding.providers import selection
                body = self._read_json_body()
                identities = sorted({c['voice'] for c in state.all_characters().values()} |
                                    set(state.voice_claims().values()) | {state.character()['voice']})
                try:
                    candidate = selection.choice(str(body.get('choice', '')))
                    operation = body.get('operation')
                    if operation == 'prepare':
                        selection.prepare(candidate)
                    elif operation == 'apply':
                        selection.apply(candidate, str(body.get('revision', '')),
                                        body.get('bindings', {}), identities, state.language)
                    else:
                        raise ValueError('Choose prepare or apply.')
                    self._respond(selection.snapshot(identities, state.language))
                except (ValueError, TypeError) as error:
                    self._respond({'error': str(error)}, status=400)
            elif self.path == "/speech-settings/transcribe":
                import base64
                import io
                import wave
                from noisy_coding.providers import selection
                from noisy_coding.providers import stt_provider
                body = self._read_json_body()
                try:
                    candidate = selection.choice(str(body.get('choice', '')))
                    if candidate['direction'] != 'stt' or selection.readiness(candidate)[0] != 'ready':
                        raise ValueError('Prepare recognition before testing it.')
                    encoded = body.get('audio', '')
                    if not isinstance(encoded, str) or len(encoded) > 1_400_000:
                        raise ValueError('Record a sample shorter than 15 seconds.')
                    audio = base64.b64decode(encoded, validate=True)
                    with wave.open(io.BytesIO(audio)) as sample:
                        if sample.getnchannels() != 1 or sample.getsampwidth() != 2 or sample.getframerate() != 16000 or sample.getnframes() > 256000:
                            raise ValueError('Use a short mono 16 kHz speech sample.')
                    provider = stt_provider(candidate['provider'], selection.options_for(candidate))
                    started = time.monotonic()
                    text = provider.transcribe(audio, '' if state.language == 'auto' else state.language)
                    self._respond({'text': text, 'elapsed_ms': round((time.monotonic() - started)*1000)})
                except (ValueError, RuntimeError, wave.Error, EOFError) as error:
                    self._respond({'error': str(error)}, status=400)
            elif self.path == "/speech-settings/preview":
                import asyncio
                import base64
                from noisy_coding.providers import selection
                from noisy_coding.providers import tts_provider
                body = self._read_json_body()
                try:
                    candidate = selection.choice(str(body.get('choice', '')))
                    if candidate['direction'] != 'tts' or selection.readiness(candidate)[0] != 'ready':
                        raise ValueError('Prepare the voice engine before previewing it.')
                    voice = str(body.get('voice', ''))
                    if voice not in {v['id'] for v in selection.voices(candidate)}:
                        raise ValueError('Choose a voice from this engine.')
                    options = selection.options_for(candidate)
                    options.pop('voice_bindings', None)  # Preview the chosen native voice, not an identity mapping.
                    provider = tts_provider(candidate['provider'], options)
                    audio = asyncio.run(provider.synthesize(
                        'The search now ignores capital letters. All twelve tests passed. Shall I deploy it?',
                        voice, 'en', 1.0))
                    self._respond({'audio': base64.b64encode(audio.audio).decode(), 'content_type': audio.content_type})
                except (ValueError, RuntimeError) as error:
                    self._respond({'error': str(error)}, status=400)
            elif self.path == "/providers":
                # Switch voice engines and/or store per-provider options.
                # The selection lives in providers.json and is re-read on
                # every synth/transcribe call — active immediately, no
                # daemon restart.
                from noisy_coding import providers
                from noisy_coding.providers import config as provider_config

                body = self._read_json_body()
                known = providers.available()
                choice: dict = {}
                for direction in ("tts", "stt"):
                    name = body.get(direction)
                    if name is None:
                        continue
                    if name not in known[direction]:
                        self._respond(
                            {"error": f"unknown {direction} provider '{name}'"},
                            status=400,
                        )
                        return
                    choice[direction] = name
                local = body.get("local")
                local = local if isinstance(local, dict) else {}
                # {"prefetch": true} alone re-kicks the downloads — the
                # RETRY button after a failed fetch.
                prefetch_requested = bool(body.get("prefetch"))
                if not choice and not local and not prefetch_requested:
                    self._respond({"error": "nothing to change"}, status=400)
                    return
                from noisy_coding.providers import selection
                if set(local) - {'stt_model', 'tts_engine', 'tts_voice'}:
                    self._respond({'error': 'Unsupported local speech option.'}, status=400)
                    return
                if local.get('stt_model', provider_config.DEFAULT_LOCAL_STT_MODEL) not in selection.WHISPER_MODELS or local.get('tts_engine', 'kokoro') not in ('kokoro', 'say'):
                    self._respond({'error': 'Choose an available local model.'}, status=400)
                    return
                pending_options = {**provider_config.local_options(), **local}
                pending_tts = choice.get('tts', provider_config.tts_provider_name()) == 'local'
                pending_stt = choice.get('stt', provider_config.stt_provider_name()) == 'local'
                if (choice or local) and (pending_tts or pending_stt):
                    from noisy_coding.providers import local as local_provider
                    if not local_provider.models_present(tts=pending_tts, stt=pending_stt, options=pending_options):
                        local_provider.prefetch_models(tts=pending_tts, stt=pending_stt, options=pending_options)
                        self._respond({'error': 'Preparing local models. Your current engines remain active; apply again after the download finishes.'}, status=409)
                        return
                if choice or local:
                    provider_config.save(
                        tts=choice.get("tts"), stt=choice.get("stt"), **local
                    )
                if prefetch_requested or "local" in (
                    provider_config.tts_provider_name(),
                    provider_config.stt_provider_name(),
                ):
                    # Fetch the weights NOW, in the background — the first
                    # utterance must find them on disk, not wait for them.
                    from noisy_coding.providers import local as local_provider

                    local_provider.prefetch_models()
                state.add_event(
                    "providers",
                    f"tts={provider_config.tts_provider_name()} "
                    f"stt={provider_config.stt_provider_name()}",
                )
                self._respond(
                    {
                        "tts": provider_config.tts_provider_name(),
                        "stt": provider_config.stt_provider_name(),
                    }
                )
            elif self.path == "/speaking":
                body = self._read_json_body()
                speaking = bool(body.get("speaking", False))
                state.set_claude_speaking(speaking, body.get("agent"))
                self._respond({"speaking": speaking})
            elif self.path == "/speak":
                self._handle_speak()
            elif self.path == "/abort-recording":
                # Scratch-my-words: kill the utterance in progress (any mode).
                state.request_recording_abort()
                self._respond({"requested": True})
            elif self.path == "/shutdown":
                # Graceful shutdown (#35): agents call this instead of kill.
                # Default 5 min countdown; the dashboard shows a banner with
                # CANCEL and RESTART NOW. The watcher (daemon.py) refuses to
                # die mid-recording.
                body = self._read_json_body()
                delay = float(body.get("delay_seconds", 300))
                # The countdown exists for the HUMAN: a 2s "graceful" restart
                # once ate a sentence mid-recording (stream day 4). Agents do
                # not get to rush it - anything under 60s is clamped UP,
                # except an exact 0, which is the dashboard's RESTART NOW
                # button: an explicit human click, the one caller allowed to
                # skip the wait.
                if 0 < delay < 60:
                    delay = 60.0
                at = state.schedule_shutdown(delay)
                state.add_event(
                    "agent", f"shutdown scheduled in {int(delay)}s (cancellable)"
                )
                self._respond({"shutdown_at": at})
            elif self.path == "/shutdown-postpone":
                body = self._read_json_body()
                seconds = float(body.get("seconds", 60))
                at = state.postpone_shutdown(seconds)
                state.add_event("agent", f"shutdown postponed by {int(seconds)}s")
                self._respond({"shutdown_at": at})
            elif self.path == "/shutdown-cancel":
                state.cancel_shutdown()
                state.add_event("agent", "shutdown cancelled")
                self._respond({"cancelled": True})
            elif self.path == "/skip-unheard":
                body = self._read_json_body()
                agent = str(body.get("agent") or "") or None
                count = state.skip_unheard(agent)
                if count:
                    state.add_event("agent", f"skipped {count} unheard message(s)")
                self._respond({"skipped": count})
            elif self.path == "/playback-pause":
                # Transport pause: freezes the system player in place; the
                # tab player (browser output) pauses itself client-side.
                paused = playback.toggle_pause()
                # Capture is muted while the agent speaks so the microphone
                # does not hear the speakers. A PAUSED clip makes no sound,
                # so that reason is gone - and leaving the mute on meant the
                # dashboard showed RECORDING while nothing was captured and
                # the user talked into a dead microphone (day 8). Pausing is
                # usually done PRECISELY in order to say something.
                if paused:
                    state.set_paused(False)
                elif state.claude_speaking:
                    state.set_paused(True)
                self._respond({"paused": paused})
            elif self.path == "/interrupt":
                # Stop whatever is on the speakers; queued speech continues.
                # The stop button is a deliberate dismissal: the clip settles
                # as SKIPPED (readable in the log, never counted for catch-up
                # again) - unlike a push-to-talk barge-in, where the clip may
                # still be worth hearing and parks as UNHEARD.
                state.interrupt_playing_as_unheard("stopped by you", label="skipped")
                playback.stop_all_players()
                live_bridge = tab_audio.bridge()
                if live_bridge is not None:
                    live_bridge.stop_tab_playback()
                self._respond({"stopped": True})
            elif self.path == "/cancel":
                utterance_id = int(self._read_json_body().get("utterance_id", 0))
                self._respond({"cancelled": state.cancel_transcript(utterance_id)})
            elif self.path == "/activity":
                body = self._read_json_body()
                agent = str(body.get("agent") or "")
                agent = state.conversations.resolve(agent) or agent
                known = state.conversations.get(agent)
                if known is None or not known.hidden:
                    state.set_activity(agent, str(body.get("text") or ""))
                self._respond({"ok": True})
            elif self.path == "/ptt":
                # Lease renewal/release for push-to-talk; the UI renews
                # while the button is held (see PTT_LEASE_SECONDS).
                if bool(self._read_json_body().get("held", False)):
                    state.refresh_ptt_hold()
                    # The held button IS the user's turn: it overrides any
                    # playback, and each renewal re-silences anything that
                    # dared to start. AUTO mode deliberately has no such
                    # barge-in — room noise must not cancel Claude's speech.
                    if state.detection_mode == "ptt":
                        playback.stop_all_players()
                else:
                    state.release_ptt()
                self._respond({"held": state.ptt_held})
            elif self.path == "/credentials":
                key = str(self._read_json_body().get("xai_api_key", "")).strip()
                if len(key) < 8:
                    self._respond({"error": "that does not look like an API key"}, status=400)
                else:
                    # Verify-then-commit: live-check every real call site
                    # with the candidate key. A key that fails the api_key
                    # check itself is NEVER accepted (the previous one, if
                    # any, is restored) — first contact must not swallow a
                    # dead key and let the user discover it utterances
                    # later. A VALID key with degraded voice endpoints is
                    # still accepted: that's xAI's outage, not the key
                    # (per-check verdicts tell the user exactly that).
                    previous_key = credentials.api_key()
                    credentials.save_api_key(key)
                    checks = diagnostics.run_checks_sync(state.set_diagnostic_checks)
                    if not checks["api_key"]["ok"]:
                        if previous_key:
                            credentials.save_api_key(previous_key)
                        else:
                            credentials.delete_api_key()
                        state.add_event(
                            "credentials_rejected",
                            checks["api_key"].get("detail", "")[:160],
                        )
                        self._respond(
                            {
                                "api_key_set": bool(previous_key),
                                "error": "the key failed verification — nothing was saved",
                                "checks": checks,
                            },
                            status=400,
                        )
                        return
                    state.add_event("credentials", "xAI API key configured")
                    failed = [name for name, c in checks.items() if not c["ok"]]
                    if failed:
                        state.add_event(
                            "credentials_check", "failing: " + ", ".join(failed)
                        )
                    else:
                        # Spoken confirmation doubles as the ultimate TTS
                        # proof: hearing it means the whole voice path works.
                        # It also hands the user their NEXT step — the mic.
                        # tab_mic_live, not tab_audio_alive: a connected tab
                        # plays audio just fine while its microphone still
                        # awaits the activation click (the yellow banner).
                        mic_pending = (
                            state.input_device == "browser"
                            and not state.tab_mic_live
                        )
                        next_step = (
                            "One step left: the microphone. Click the ENABLE "
                            "TAB AUDIO banner at the top of the page and allow "
                            "microphone access when your browser asks — then "
                            "just say hello."
                            if mic_pending
                            else "Your microphone is already live — just start talking."
                        )
                        speech.submit(
                            state,
                            "New xAI key accepted — every voice check passed, "
                            "and you are hearing the proof right now. " + next_step,
                            role="daemon",  # Noisy Studio speaks for itself here
                        )
                    self._respond(
                        {
                            "api_key_set": True,
                            "api_key_hint": credentials.api_key_hint(),
                            "checks": checks,
                        }
                    )
            elif self.path == "/voice-mute":
                muted = bool(self._read_json_body().get("muted", True))
                state.set_voice_muted(muted)
                if muted:
                    # Mute means silence NOW: kill the playing clip and park
                    # it unheard (cut short ≠ played; catch-up replays it).
                    if state.interrupt_playing_as_unheard("voice muted"):
                        playback.stop_all_players()
                        live_bridge = tab_audio.bridge()
                        if live_bridge is not None:
                            live_bridge.stop_tab_playback()
                state.add_event("voice_muted" if muted else "voice_unmuted")
                self._respond({"voice_muted": muted})
            elif self.path == "/mute":
                muted = bool(self._read_json_body().get("muted", True))
                state.set_user_muted(muted)
                state.add_event("muted" if muted else "unmuted")
                self._respond({"muted": muted})
            elif self.path == "/mode":
                body = self._read_json_body()
                mode = str(body.get("mode", ""))
                if mode in ("batch", "live"):
                    state.set_mode(mode)
                    state.add_event("mode", f"transcription mode switched to {mode}")
                    save_settings(state)
                    self._respond({"mode": mode})
                else:
                    self._respond({"error": "mode must be 'batch' or 'live'"}, status=400)
            elif self.path == "/event":
                body = self._read_json_body()
                kind = str(body.get("kind", "event"))
                detail = str(body.get("detail", ""))
                state.add_event(kind, detail)
                self._track_speak_utterance(kind, detail, body)
                self._respond({"ok": True})
            else:
                self._respond({"error": "not found"}, status=404)

        def _serve_hud_file(self, relative: str) -> None:
            if not DIST_DIR.is_dir():
                self._respond_html(BUILD_HINT_HTML)
                return
            target = (DIST_DIR / relative).resolve()
            # Never serve anything outside dist (path traversal guard).
            if not target.is_relative_to(DIST_DIR.resolve()):
                self._respond({"error": "not found"}, status=404)
                return
            if not target.is_file():
                # The HUD routes on pathname (/debug, /logs, /companion), so a
                # path with no file behind it is a VIEW, not a mistake - hand
                # back the entry point and let the app route it. Anything with
                # an extension really is missing: a 404 for a stylesheet must
                # not arrive as a page of HTML.
                if target.suffix:
                    self._respond({"error": "not found"}, status=404)
                    return
                target = DIST_DIR / "index.html"
                if not target.is_file():
                    self._respond({"error": "not found"}, status=404)
                    return
            payload = target.read_bytes()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                STATIC_CONTENT_TYPES.get(target.suffix, "application/octet-stream"),
            )
            # Cache policy (#21): the HTML entry point must revalidate on
            # every load or a heuristically-cached index keeps pointing at
            # the PREVIOUS build's hashed assets (half-old, half-new UI
            # after an update). Vite's content-hashed /assets/ are safe to
            # cache forever; unhashed root statics (sprite, favicons) get
            # a modest hour.
            if target.suffix == ".html":
                self.send_header("Cache-Control", "no-cache")
            elif "assets" in target.parts:
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            else:
                self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _stream_mic_levels(self) -> None:
            # Server-sent events: ONE long-lived connection per dashboard
            # tab instead of high-frequency polling. ThreadingHTTPServer
            # gives the stream its own (daemon) thread; the browser's
            # EventSource reconnects on its own after daemon restarts.
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                while True:
                    payload = json.dumps(
                        {"level": state.mic_level, "recording": state.recording}
                    )
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(MIC_STREAM_INTERVAL_SECONDS)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass  # client went away — just end the stream

        def _handle_speak(self) -> None:
            # Body: {text, voice_id?, language?, speed?, interrupt?, agent?,
            # wait?}. wait=true (default) blocks until the utterance has
            # played — that's the `speak` tool's "wait until it's said"
            # semantics; wait=false is `announce` (fire-and-forget).
            body = self._read_json_body()
            text = str(body.get("text", "")).strip()
            if not text:
                self._respond({"error": "text required"}, status=400)
                return
            source_id = int(body.get("source_id", 0))
            if source_id and speech.replay_in_flight(source_id):
                # This bubble is already queued/playing — repeated clicks
                # must not stack replays (nor interrupt the one in flight),
                # so bail BEFORE the interrupt below can do any damage.
                self._respond({"skipped": True})
                return
            claimed = str(body.get("agent") or "")
            if claimed:
                body = {**body, "agent": _revive_if_known(state, claimed)}
            if body.get("interrupt"):
                # Cut the current utterance short — wherever it is playing:
                # local player processes AND the browser tab. BEFORE submit,
                # so the stop can never race ahead and cut down the very
                # clip we are about to queue. Scoped to the caller's OWN
                # conversation: an agent may cut its own stale sentence, it
                # may not cut another agent off mid-word (2026-09-13). If
                # someone else is speaking, the new clip simply queues.
                playing = state.playing_clip()
                owner = (playing or {}).get("agent") if playing else None
                if playing is None or owner in (None, body.get("agent")):
                    state.interrupt_playing_as_unheard("replaced by a newer message")
                    playback.stop_all_players()
                    live_bridge = tab_audio.bridge()
                    if live_bridge is not None:
                        live_bridge.stop_tab_playback()
                else:
                    state.add_event("speak_wait", "interrupt ignored — another conversation is speaking")
            agent, speaker, voice_override = _resolve_speaker(state, body)
            if state.take_voice_claims_dirty():
                save_voice_claims(state)
            future = speech.submit(
                state,
                text,
                agent=agent,
                card=bool(body.get("card", True)),
                source_id=source_id,
                speaker=speaker,
                voice_override=voice_override,
            )
            if future is None:
                self._respond({"skipped": True})  # dedup raced us — same answer
                return
            if not body.get("wait", True):
                self._respond({"queued": True})
                return
            try:
                voice = future.result()
            except Exception as error:  # surface synth/playback failure to caller
                self._respond({"error": str(error)[:300]}, status=500)
                return
            self._respond({"voice": voice})

        def _track_speak_utterance(self, kind: str, detail: str, body: dict) -> None:
            # The speaking agent tags its own utterance so it lands in that
            # agent's history — even if a different agent is active by now.
            agent = body.get("agent") or state.active_agent
            # Speaking resets the narration-nudge silence clock (#16).
            state.note_agent_spoke(agent)
            if kind == "speak":
                utterance_id = state.create_utterance(
                    "claude", "synthesizing (Grok TTS)…", text=detail, agent=agent
                )
                chars = int(body.get("chars", 0))
                if chars:
                    cost = pricing.tts_cost_usd(chars)
                    state.add_cost("claude", cost)
                    state.update_utterance(utterance_id, cost_usd=cost)
            elif kind == "speak_audio":
                state.update_utterance(
                    state.latest_utterance_id("claude", agent),
                    status="playing through speakers…",
                    detail=detail,
                )
            elif kind == "speak_done":
                state.update_utterance(
                    state.latest_utterance_id("claude", agent), status="played"
                )

        def _read_json_body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                return {}

        def _respond(self, body: dict, status: int = 200) -> None:
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _respond_html(self, html: str) -> None:
            payload = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: object) -> None:
            pass  # keep the daemon's stdout for transcript logs only

    return Handler


def start_http_api(state: ListenerState, port: int) -> ThreadingHTTPServer:
    host = os.environ.get(BIND_ENV_VAR, "127.0.0.1")
    server = ThreadingHTTPServer((host, port), _handler_class(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
