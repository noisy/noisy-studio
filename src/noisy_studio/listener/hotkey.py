"""System-wide push-to-talk hotkeys (#25, chords and per-tab keys #104).

A Quartz event tap sees the configured chords no matter which app has
focus and drives the SAME push-to-talk lease the dashboard button uses:

- hold:    key down opens the lease, key up releases it;
- toggle:  one press opens, the next press releases;
- scratch: abort the recording in progress, in any mode;
- tabN:    select the N-th visible conversation and toggle the lease -
           press again to close, another tab's key hands the mic over.

macOS only: the tap needs the Input Monitoring permission (System
Settings > Privacy & Security > Input Monitoring) for the process that
runs the daemon. The permission is never requested at boot (#97): a
prompt about "receiving keystrokes from any application" the moment an
app is installed reads as hostile. It is requested when the user picks a
hotkey, or presses the grant button in settings, and until granted the
configured keys stay disarmed and /status says so. On other platforms,
or when no key is configured, this module is a silent no-op.

The lease is renewed from a small thread while engaged, exactly like
the dashboard's ~2x/s heartbeat, so daemon-side expiry keeps working
if this process dies mid-hold.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Protocol

from noisy_studio.listener.chords import (
    DOUBLE_TAP_SECONDS,
    Chord,
    ChordError,
    MODIFIER_KEYS,
    parse_chord,
    problems,
)

# Every action a chord can drive. "tabN" = toggle-to-talk aimed at the N-th
# visible conversation (#104). Settings store {action: chord text}.
ACTIONS = ("hold", "toggle", "scratch", "tab1", "tab2", "tab3", "tab4")
TAB_ACTIONS = {f"tab{i}": i for i in range(1, 5)}
# What a fresh install gets, and what fills an action the user never touched.
# F16-F19 type nothing anywhere; a double Escape never fires by accident.
DEFAULT_HOTKEYS = {"scratch": "escape x2", "tab1": "F16", "tab2": "F17", "tab3": "F18", "tab4": "F19"}

LEASE_RENEW_SECONDS = 0.4  # matches the dashboard's heartbeat cadence


def _quartz():
    """The Quartz bridge, or None off macOS. One seam for the tests."""
    try:
        import Quartz  # noqa: PLC0415

        return Quartz
    except ImportError:
        return None


def input_monitoring_status() -> str:
    """"granted" | "missing" | "unavailable" (non-macOS or old pyobjc)."""
    quartz = _quartz()
    if quartz is None or not hasattr(quartz, "CGPreflightListenEventAccess"):
        return "unavailable"
    return "granted" if quartz.CGPreflightListenEventAccess() else "missing"


def request_input_monitoring() -> str:
    """Ask macOS (it shows its prompt once; a refusal must be undone in
    System Settings). Returns the status afterwards."""
    quartz = _quartz()
    if quartz is None or not hasattr(quartz, "CGRequestListenEventAccess"):
        return "unavailable"
    return "granted" if quartz.CGRequestListenEventAccess() else "missing"


class _PttState(Protocol):
    def refresh_ptt_hold(self) -> None: ...
    def release_ptt(self) -> None: ...
    def request_recording_abort(self) -> None: ...
    def talk_to_tab(self, index: int) -> bool: ...


class HotkeyListener:
    """Owns the event tap thread and the lease-renewal thread."""

    def __init__(self, state: _PttState, log: Callable[[str], None]) -> None:
        self._state = state
        self._log = log
        self._lock = threading.Lock()
        self._bindings: dict[str, Chord] = {}
        self._problems: dict[str, dict[str, str]] = {}
        self._modifier_down: set[int] = set()
        self._engaged = False          # lease currently open (either mode)
        self._toggle_latched = False   # toggle mode: waiting for 2nd press
        self._tab_latched: int | None = None  # which tabN opened the lease
        self._tap_thread: threading.Thread | None = None
        self._renew_thread: threading.Thread | None = None
        self._restart = None  # CFRunLoop stop handle, set by the tap thread
        self._permission = "unknown"  # last probe: granted | missing | unavailable
        self._last_down: dict[str, float] = {}  # action -> time of previous press (x2 chords)
        self._clock = time.monotonic

    # -- configuration ----------------------------------------------------

    def configure(
        self, hold_key: str, toggle_key: str, cancel_key: str = "", *, may_prompt: bool = False
    ) -> None:
        """Legacy three-key form; keeps the other actions as they are."""
        current = {a: str(c) for a, c in self._bindings.items()}
        current.update({"hold": hold_key, "toggle": toggle_key, "scratch": cancel_key})
        self.configure_bindings(current, may_prompt=may_prompt)

    def configure_bindings(self, bindings: dict[str, str], *, may_prompt: bool = False) -> None:
        """Apply {action: chord text} from settings; restarts the tap as needed.

        Unparseable or colliding chords are recorded as problems and NOT
        armed - the other bindings still work. `may_prompt` is True only on
        a user action (picking a key): that is the one moment macOS may show
        its Input Monitoring prompt. Boot never prompts; keys restored from
        settings stay disarmed until the permission is there (#97)."""
        text = {a: (bindings.get(a) or "") for a in ACTIONS}
        found = problems(text)
        armed: dict[str, Chord] = {}
        for action, chord_text in text.items():
            if not chord_text or found.get(action, {}).get("kind") in ("invalid", "collision"):
                continue
            try:
                chord = parse_chord(chord_text)
            except ChordError:
                continue
            if chord.taps == 2 and action == "hold":
                # Hold needs the key-up of the SAME press; a double press has none.
                found[action] = {"kind": "invalid", "detail": "hold cannot be a double press"}
                continue
            armed[action] = chord
        with self._lock:
            self._bindings = armed
            self._problems = found
            wanted = bool(armed)
        self._disengage()
        self._stop_tap()
        if not wanted:
            return
        self._arm(may_prompt=may_prompt)

    def _arm(self, *, may_prompt: bool) -> None:
        status = input_monitoring_status()
        if status == "missing" and may_prompt:
            status = request_input_monitoring()
        with self._lock:
            self._permission = status
        if status == "missing":
            self._log(
                "hotkey: keys configured but Input Monitoring not granted - "
                "global PTT disarmed until the user grants it in settings"
            )
            return
        self._start_tap()

    def request_permission(self) -> dict:
        """The settings GRANT button: prompt now, arm if granted."""
        with self._lock:
            wanted = bool(self._bindings)
        if wanted:
            self._stop_tap()
            self._arm(may_prompt=True)
        else:
            with self._lock:
                self._permission = request_input_monitoring()
        return self.snapshot()

    def snapshot(self) -> dict:
        """For /status: what the dashboard needs to explain the hotkey state.

        Re-probes Input Monitoring every time (CGPreflightListenEventAccess
        is cheap): a grant revoked in System Settings disarms the keys and
        brings the GRANT banner back; a grant given there arms them without
        a prompt. Never prompts - that stays a user action (#97)."""
        self._refresh_permission()
        with self._lock:
            return {
                "configured": bool(self._bindings),
                "permission": self._permission,
                "armed": bool(self._bindings) and self._tap_thread is not None,
                "bindings": {a: str(c) for a, c in self._bindings.items()},
                "problems": dict(self._problems),
            }

    def _refresh_permission(self) -> None:
        with self._lock:
            configured = bool(self._bindings)
            previous = self._permission
            armed = self._tap_thread is not None
        if not configured:
            return
        status = input_monitoring_status()
        if status == "unavailable" or status == previous and (status != "granted" or armed):
            return
        with self._lock:
            self._permission = status
        if status == "missing" and armed:
            self._log("hotkey: Input Monitoring revoked - global PTT disarmed")
            self._disengage()
            self._stop_tap()
        elif status == "granted" and not armed:
            self._log("hotkey: Input Monitoring granted - arming")
            self._start_tap()

    # -- lease driving -----------------------------------------------------

    def _engage(self) -> None:
        with self._lock:
            if self._engaged:
                return
            self._engaged = True
        self._state.refresh_ptt_hold()
        self._renew_thread = threading.Thread(target=self._renew_loop, daemon=True)
        self._renew_thread.start()

    def _disengage(self) -> None:
        with self._lock:
            was = self._engaged
            self._engaged = False
            self._toggle_latched = False
            self._tab_latched = None
        if was:
            self._state.release_ptt()

    def _renew_loop(self) -> None:
        while True:
            with self._lock:
                if not self._engaged:
                    return
            self._state.refresh_ptt_hold()
            time.sleep(LEASE_RENEW_SECONDS)

    # -- dispatch ------------------------------------------------------------

    def _on_event(self, keycode: int, flags: int, down: bool) -> None:
        """One tap event -> the action whose chord it fires, if any. An x2
        chord fires on the second press within DOUBLE_TAP_SECONDS."""
        with self._lock:
            hit = [(a, c) for a, c in self._bindings.items() if _matches(c.base, keycode, flags)]
        for action, chord in hit:
            if chord.taps == 2:
                if not down:
                    continue
                now = self._clock()
                previous = self._last_down.get(action)
                if previous is not None and now - previous <= DOUBLE_TAP_SECONDS:
                    self._last_down.pop(action, None)
                    self._run(action, True)
                else:
                    self._last_down[action] = now
                continue
            self._run(action, down)

    def _run(self, action: str, down: bool) -> None:
        if action == "scratch":
            if down:
                # Scratch-my-words: abort the recording in ANY mode, and if a
                # latch is open, close it - the turn is over either way.
                self._state.request_recording_abort()
                self._disengage()
        elif action == "hold":
            if down:
                self._engage()
            else:
                self._disengage()
        elif action == "toggle" and down:
            # The global toggle also CLOSES a lease a tab key opened: start
            # talking to tab 2 with its key, finish with the toggle you
            # always use.
            with self._lock:
                open_lease = self._engaged
            if open_lease:
                self._disengage()
            else:
                with self._lock:
                    self._toggle_latched = True
                self._engage()
        elif action in TAB_ACTIONS and down:
            index = TAB_ACTIONS[action]
            if self._tab_latched == index:
                self._disengage()          # second press on the same tab closes
                return
            if not self._state.talk_to_tab(index):
                self._log(f"hotkey: no visible conversation #{index}")
                return
            self._disengage()              # hand-over from another tab / toggle
            with self._lock:
                self._tab_latched = index
            self._engage()

    # -- the tap -----------------------------------------------------------

    def _start_tap(self) -> None:
        Quartz = _quartz()  # noqa: N806 - reads like the module below
        if Quartz is None:
            self._log("hotkey: Quartz unavailable (non-macOS) — global PTT off")
            return

        def run() -> None:
            with self._lock:
                watched_modifiers = {
                    c.keycode for c in self._bindings.values() if c.key in MODIFIER_KEYS
                }
                summary = ", ".join(f"{a}={c}" for a, c in self._bindings.items())

            def callback(_proxy, event_type, event, _refcon):
                keycode = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventKeycode
                )
                flags = Quartz.CGEventGetFlags(event)
                if event_type == Quartz.kCGEventFlagsChanged:
                    if keycode in watched_modifiers:
                        down = keycode not in self._modifier_down
                        if down:
                            self._modifier_down.add(keycode)
                        else:
                            self._modifier_down.discard(keycode)
                        self._on_event(keycode, flags, down)
                elif event_type in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
                    # Ignore key-repeat: a held F-key fires repeats that
                    # would flap the toggle.
                    if event_type == Quartz.kCGEventKeyDown and Quartz.CGEventGetIntegerValueField(
                        event, Quartz.kCGKeyboardEventAutorepeat
                    ):
                        return event
                    self._on_event(keycode, flags, event_type == Quartz.kCGEventKeyDown)
                return event  # listen-only: never swallow the key

            mask = (
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
                | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
                | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
            )
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                mask,
                callback,
                None,
            )
            if tap is None:
                self._log(
                    "hotkey: event tap refused — grant Input Monitoring to Noisy Studio "
                    "(System Settings > Privacy & Security > Input Monitoring)"
                )
                with self._lock:
                    self._permission = "missing"
                    self._tap_thread = None
                return
            source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
            loop = Quartz.CFRunLoopGetCurrent()
            Quartz.CFRunLoopAddSource(loop, source, Quartz.kCFRunLoopCommonModes)
            Quartz.CGEventTapEnable(tap, True)
            self._restart = loop
            self._log(f"hotkey: global PTT armed ({summary})")
            Quartz.CFRunLoopRun()

        self._tap_thread = threading.Thread(target=run, daemon=True, name="ptt-hotkey")
        self._tap_thread.start()

    def _stop_tap(self) -> None:
        loop = self._restart
        if loop is not None:
            try:
                Quartz = _quartz()  # noqa: N806
                if Quartz is not None:
                    Quartz.CFRunLoopStop(loop)
            except Exception:
                pass
            self._restart = None
        self._tap_thread = None


def _matches(chord: Chord, keycode: int, flags: int) -> bool:
    from noisy_studio.listener.chords import matches

    return matches(chord, keycode, flags)
