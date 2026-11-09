"""Deadlines for PortAudio calls that can block forever.

On macOS, stopping, closing or re-initializing an input stream while
CoreAudio is mid-change (a USB headset dongle vanishing and reappearing,
sleep/wake) can block inside PortAudio indefinitely. The capture loop made
those calls inline, so one stuck call froze microphone capture for the rest
of the run: no log line, no error event, no further recordings, while
playback kept working.

The guard runs each call on a worker thread and waits a bounded time. A
call that overruns is abandoned and reported; until it returns, further
calls are refused instead of piling onto a wedged audio system, and the
capture loop keeps running and retrying.
"""

from __future__ import annotations

import threading
from typing import Callable, TypeVar

T = TypeVar("T")

# Healthy stop/close/open/reinit calls finish in well under a second.
AUDIO_CALL_TIMEOUT_SECONDS = 5.0
# A stream that keeps delivering nothing (the fallback device is dead too,
# or the machine sleeps) used to be torn down and reopened every two seconds
# for as long as it lasted - hundreds of PortAudio reinits that flood the
# log and churn CoreAudio. Back off instead.
STALL_RETRY_MAX_SECONDS = 60.0


def stall_retry_seconds(streak: int, base: float) -> float:
    """Wait before the next reopen after `streak` consecutive silent reopens."""
    return min(base * 2 ** min(streak, 16), STALL_RETRY_MAX_SECONDS)


class AudioCallGuard:
    def __init__(self, log: Callable[[str], None], timeout: float = AUDIO_CALL_TIMEOUT_SECONDS):
        self._log = log
        self._timeout = timeout
        self._stuck: threading.Thread | None = None
        self._stuck_label = ""

    @property
    def wedged(self) -> bool:
        """True while an abandoned call is still blocked inside PortAudio."""
        if self._stuck is not None and not self._stuck.is_alive():
            self._log(f"[mic] {self._stuck_label} finally returned — audio calls resume")
            self._stuck = None
        return self._stuck is not None

    def run(
        self,
        label: str,
        call: Callable[[], T],
        *,
        on_late_result: Callable[[T], None] | None = None,
    ) -> tuple[bool, T | None]:
        """Run `call` with a deadline.

        Returns (True, value) when it finished in time; exceptions it raised
        are re-raised here. Returns (False, None) when it overran or another
        call is still stuck. A value produced after the deadline goes to
        `on_late_result` (e.g. to close a stream nobody holds anymore).
        """
        if self.wedged:
            return False, None
        outcome: dict[str, object] = {}
        lock = threading.Lock()

        def target() -> None:
            try:
                value = call()
            except BaseException as error:  # noqa: BLE001 - handed back to the caller
                with lock:
                    outcome["error"] = error
                return
            with lock:
                if not outcome.get("abandoned"):
                    outcome["value"] = value
                    return
            if on_late_result is not None:
                try:
                    on_late_result(value)
                except Exception:  # noqa: BLE001 - nobody is waiting for this thread
                    pass

        worker = threading.Thread(target=target, name=f"audio-call: {label}", daemon=True)
        worker.start()
        worker.join(self._timeout)
        with lock:
            if worker.is_alive() and "value" not in outcome and "error" not in outcome:
                outcome["abandoned"] = True
                self._stuck = worker
                self._stuck_label = label
                self._log(
                    f"[mic] {label} did not return within {self._timeout:.0f}s — "
                    "abandoning it; the audio system is not responding"
                )
                return False, None
        if "error" in outcome:
            raise outcome["error"]  # type: ignore[misc]
        return True, outcome.get("value")  # type: ignore[return-value]
