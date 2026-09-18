"""Which provider is active, per direction — one small file, read per call.

Same philosophy as credentials.py: no env-var maze, one source of truth
in the config dir, and because every call re-reads it, switching provider
is a file write — no daemon restart. A missing file uses defaults. An unreadable or malformed existing file
stops provider selection instead of silently falling back to an online service.

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
import shutil
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


class ConfigurationError(ValueError):
    """Saved speech choices cannot be used safely; never include their contents."""


def _settings_error() -> ConfigurationError:
    return ConfigurationError(
        'Saved speech settings are unreadable or invalid. No fallback engine was selected. '
        'Restore providers.json from a valid backup, then retry.'
    )


def _read() -> dict[str, Any]:
    try:
        data = json.loads(PROVIDERS_FILE.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        raise _settings_error() from None
    if not isinstance(data, dict):
        raise _settings_error()
    for direction in ('stt', 'tts'):
        if direction in data and (not isinstance(data[direction], str) or not data[direction].strip()):
            raise _settings_error()
    local = data.get('local', {})
    providers = data.get('providers', {})
    if not isinstance(local, dict) or not isinstance(providers, dict):
        raise _settings_error()
    for options in [local, *providers.values()]:
        if not isinstance(options, dict):
            raise _settings_error()
        bindings = options.get('voice_bindings', {})
        catalogs = options.get('voice_bindings_by_engine', {})
        if not isinstance(catalogs, dict):
            raise _settings_error()
        for mapping in [bindings, *catalogs.values()]:
            if not isinstance(mapping, dict) or any(not isinstance(voice, str) for voice in mapping.values()):
                raise _settings_error()
    for field in ('stt_model', 'tts_engine', 'tts_voice'):
        if field in local and not isinstance(local[field], str):
            raise _settings_error()
    return data


def tts_provider_name() -> str:
    return str(_read().get("tts") or DEFAULT_TTS)


def stt_provider_name() -> str:
    return str(_read().get("stt") or DEFAULT_STT)


def local_options() -> dict[str, Any]:
    return provider_options("local")


def provider_options(provider: str) -> dict[str, Any]:
    """Provider-owned settings, retaining the existing local file layout."""
    data = _read()
    if provider == "local":
        options = data.get("local")
    else:
        options = data.get("providers", {}).get(provider)
    return dict(options) if isinstance(options, dict) else {}


def save_selection(direction: str, provider: str, options: dict[str, Any]) -> None:
    """Atomically select one direction and retain every other provider's settings."""
    if direction not in ("stt", "tts"):
        raise ValueError("Unknown speech direction")
    with _lock:
        data = _read()
        data[direction] = provider
        if provider == "local":
            data["local"] = {**data.get("local", {}), **options}
        else:
            settings = dict(data.get("providers", {}))
            settings[provider] = {**settings.get(provider, {}), **options}
            data["providers"] = settings
        _write(data)


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
    _write(data)


def _write(data):
    PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    backup = PROVIDERS_FILE.with_suffix(".json.bak")
    if PROVIDERS_FILE.exists() and not backup.exists():
        shutil.copy2(PROVIDERS_FILE, backup)
    with tempfile.NamedTemporaryFile(mode="w", dir=PROVIDERS_FILE.parent, delete=False) as output:
        path = output.name
        json.dump(data, output, indent=2)
    try:
        os.replace(path, PROVIDERS_FILE)
    finally:
        if os.path.exists(path):
            os.unlink(path)
