"""Dictate anywhere: speech goes into the focused text field, not to an agent.

The dictate hotkey toggles a dictation session. While it is on, the audio
loop records exactly like toggle-to-talk, but every utterance it opens is
stamped with the session number instead of a conversation. When such an
utterance is transcribed, ListenerState hands the text here instead of
queueing it, and it is inserted into the frontmost app. It never reaches an
agent.

A session is one press-to-press stretch. A long one can be split into
several utterances (max utterance length); they are inserted in order, and
every segment after the first gets a leading space so the words do not run
together.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Protocol

from noisy_studio.listener import text_insertion
from noisy_studio.listener.caret import Anchor, CaretLocator
from noisy_studio.listener.text_insertion import InsertionError

MUTED_HINT = "Dictation needs the microphone: it is muted"
PERMISSION_HINT = (
    "Dictation needs the Accessibility permission to paste into other apps: "
    "System Settings > Privacy & Security > Accessibility"
)


class _Inserter(Protocol):
    def insert(self, text: str) -> text_insertion.Insertion: ...


class _Locator(Protocol):
    def locate(self) -> Anchor | None: ...


class _DictationState(Protocol):
    @property
    def user_muted(self) -> bool: ...
    def dictation_pending(self, session: int) -> bool: ...
    def set_dictation_session(self, session: int) -> None: ...
    def update_utterance(self, utterance_id: int, **fields: str) -> None: ...
    def add_event(self, kind: str, detail: str = "") -> None: ...


class Dictation:
    """Starts and stops sessions and inserts their transcripts, in order."""

    def __init__(
        self,
        state: _DictationState,
        log: Callable[[str], None],
        inserter: _Inserter | None = None,
        status: Callable[[], str] = text_insertion.accessibility_status,
        request: Callable[[], str] = text_insertion.request_accessibility,
        executor: ThreadPoolExecutor | None = None,
        locator: _Locator | None = None,
    ) -> None:
        self._state = state
        self._log = log
        self._inserter = inserter if inserter is not None else text_insertion.PasteInserter()
        self._status = status
        self._request = request
        self._locator = locator if locator is not None else CaretLocator()
        # One worker: segments of a session must land in the order spoken,
        # and the restore delay must not hold up the next transcription.
        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="dictation")
        self._lock = threading.Lock()
        self._session = 0          # number of the running session, 0 = off
        self._last_session = 0     # sessions are numbered from 1
        self._inserted_in = 0      # the session whose first segment is already in
        self._anchor: Anchor | None = None  # where the overlay opens (last session)

    # -- sessions ------------------------------------------------------------

    @property
    def active(self) -> bool:
        with self._lock:
            return self._session != 0

    def start(self) -> bool:
        """The dictate key, first press. False (and nothing recorded) when
        macOS will not let us paste: pressing the key is a user action, so
        this is a moment the permission prompt may appear (#97)."""
        refusal = self._refusal()
        if refusal:
            self._log(f"dictation: {refusal}")
            self._state.add_event("dictation_error", refusal)
            return False
        with self._lock:
            self._last_session += 1
            self._session = self._last_session
            self._anchor = None
            session = self._session
        self._state.set_dictation_session(session)
        # Off the hotkey thread: AX queries a busy app can take a while.
        self._executor.submit(self._locate, session)
        self._state.add_event("dictation", "started — speak, press the key again to insert")
        return True

    def stop(self) -> None:
        with self._lock:
            was = self._session
            self._session = 0
        if was:
            self._state.set_dictation_session(0)
            self._state.add_event("dictation", "stopped")

    def _locate(self, session: int) -> None:
        anchor = self._locator.locate()
        with self._lock:
            if self._last_session == session:
                self._anchor = anchor

    # -- transcripts -----------------------------------------------------------

    def deliver(self, text: str, utterance_id: int, session: int) -> None:
        """A dictation utterance was transcribed: insert it, off this thread."""
        self._executor.submit(self._insert, text, utterance_id, session)

    def _insert(self, text: str, utterance_id: int, session: int) -> None:
        with self._lock:
            follows_segment = self._inserted_in == session
        piece = f" {text}" if follows_segment else text
        try:
            result = self._inserter.insert(piece)
        except InsertionError as error:
            self._log(f"dictation: not inserted ({error})")
            self._state.update_utterance(utterance_id, status=f"dictation — not inserted: {error}")
            self._state.add_event("dictation_error", str(error))
            return
        except Exception as error:  # noqa: BLE001 - a dictation must never kill the worker
            self._log(f"dictation: insertion failed ({error!r})")
            self._state.update_utterance(utterance_id, status="dictation — insertion failed")
            self._state.add_event("dictation_error", repr(error)[:200])
            return
        with self._lock:
            self._inserted_in = session
        where = f" into {result.app}" if result.app else ""
        self._log(f"dictation: inserted {len(piece)} chars{where}")
        self._state.update_utterance(utterance_id, status=f"dictation — inserted{where}")

    # -- permission ------------------------------------------------------------

    def _refusal(self) -> str:
        """Why a dictation cannot start now, or "" when it can."""
        if self._state.user_muted:
            return MUTED_HINT
        status = self._status()
        if status == "missing":
            status = self._request()
        if status == "unavailable":
            return "Dictation pastes through macOS; it is not available on this system"
        return PERMISSION_HINT if status != "granted" else ""

    def request_permission(self) -> dict:
        """The settings GRANT button."""
        self._request()
        return self.snapshot()

    def snapshot(self) -> dict:
        """For /status. Re-probes (cheap, never prompts) so a grant given in
        System Settings shows up without a restart."""
        with self._lock:
            session = self._last_session
            active = self._session != 0
            anchor = self._anchor
        return {
            "permission": self._status(),
            "active": active,
            # The live overlay: which session's words to show, where the
            # text cursor was when it started, and whether its words are
            # still on their way into the app (recording, transcribing,
            # pasting) after the key stopped it.
            "session": session,
            "anchor": anchor.as_dict() if anchor else None,
            "pending": bool(session) and self._state.dictation_pending(session),
        }
