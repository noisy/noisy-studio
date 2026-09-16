"""Which provider is active, per direction — one small file, read per call.

Same philosophy as credentials.py: no env-var maze, one source of truth
in the config dir, and because every call re-reads it, switching provider
is a file write — no daemon restart. The file is optional; missing or
broken means the defaults (Grok both ways).

providers.json shape:

    {
      "tts": "grok",
      "stt": "local",
      "local": {"stt_model": "small", "tts_voice": ""}
    }
"""

import json
import os
import tempfile
import threading
from typing import Any

from noisy_coding.config_dir import CONFIG_DIR

PROVIDERS_FILE = CONFIG_DIR / "providers.json"

_lock = threading.RLock()

DEFAULT_TTS = "grok"
DEFAULT_STT = "grok"
# "base" per the 2026-08-31 benchmark: small is 2.6x realtime (5.9 s for a
# 15 s utterance) on this class of machine, base is 8.6x with quality that
# holds for dictation; tiny (16x) stays a manual pick where speed rules.
DEFAULT_LOCAL_STT_MODEL = "base"


def _read() -> dict[str, Any]:
    try:
        data = json.loads(PROVIDERS_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def tts_provider_name() -> str:
    return str(_read().get("tts") or DEFAULT_TTS)


def stt_provider_name() -> str:
    return str(_read().get("stt") or DEFAULT_STT)


def local_options() -> dict[str, Any]:
    options = _read().get("local")
    return options if isinstance(options, dict) else {}


def save(tts: str | None = None, stt: str | None = None, **local: Any) -> None:
    """Update the selection, keeping unspecified fields as they are."""
    with _lock:
        _save(tts, stt, local)


def _save(tts, stt, local):
    data = _read()
    if tts is not None:
        data["tts"] = tts
    if stt is not None:
        data["stt"] = stt
    if local:
        data["local"] = {**data.get("local", {}), **local}
    PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=PROVIDERS_FILE.parent, delete=False) as output:
        path = output.name
        json.dump(data, output, indent=2)
    try:
        os.replace(path, PROVIDERS_FILE)
    finally:
        if os.path.exists(path):
            os.unlink(path)
