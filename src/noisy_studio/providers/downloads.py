"""Model-download bookkeeping for local providers.

Big weights (Kokoro ~340 MB, whisper models) must never surprise the
user as dead air on the first utterance. So:

- every download reports into this registry (bytes done / total where
  the source gives us a length, coarse downloading/done otherwise),
- the dashboard polls it via GET /providers and draws progress bars,
- prefetch() starts the fetches in a background thread the moment the
  user picks a local engine, so weights arrive while they read the
  settings page, not while they wait for an answer.
"""

import threading
from typing import Any, Callable

_lock = threading.Lock()
# name -> {"label", "state": missing|downloading|done|error,
#          "done_bytes", "total_bytes", "detail"}
_status: dict[str, dict[str, Any]] = {}
_prefetch_running = False


def report(
    name: str,
    label: str,
    state: str,
    done_bytes: int = 0,
    total_bytes: int = 0,
    detail: str = "",
) -> None:
    with _lock:
        _status[name] = {
            "name": name,
            "label": label,
            "state": state,
            "done_bytes": done_bytes,
            "total_bytes": total_bytes,
            "detail": detail,
        }


def status() -> list[dict[str, Any]]:
    with _lock:
        return [dict(entry) for entry in _status.values()]


def prefetch(targets: list[Callable[[], None]]) -> bool:
    """Run the given fetchers in one background thread; False if one is
    already running (the poll will show its progress either way)."""
    global _prefetch_running
    with _lock:
        if _prefetch_running:
            return False
        _prefetch_running = True

    def run() -> None:
        global _prefetch_running
        try:
            for fetch in targets:
                try:
                    fetch()
                except Exception:
                    pass  # the registry holds the error entry; polls surface it
        finally:
            with _lock:
                _prefetch_running = False

    threading.Thread(target=run, name="model-prefetch", daemon=True).start()
    return True
