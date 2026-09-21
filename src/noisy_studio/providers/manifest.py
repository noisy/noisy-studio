"""What each provider needs from the user — data for a generic setup UI.

First-contact today hardwires "paste your xAI key". With multiple
engines the dashboard must instead ask "which provider?" first, then
render THAT provider's own requirements — so every provider declares
them here as plain data. The dashboard renders fields it has never
heard of; adding a provider never means new frontend code.

Field kinds the UI understands:
  - "secret": a credential (masked input, stored via its `store`)
  - "choice": pick one of `options`
  - "text":   free-form value

`ready` says whether the provider could work right now (key present,
optional dependency installed, binary on PATH) — and when it is False,
`ready_detail` says WHY and how to fix it, so the UI never shows a bare
"NOT READY" the user can't act on.
"""

import shutil
from importlib.util import find_spec
from typing import Any

from noisy_studio import credentials
from noisy_studio.providers import config


def catalog() -> list[dict[str, Any]]:
    """Every known provider, its capabilities and setup requirements."""
    return [
        {
            "name": "grok",
            "kind": "cloud-api",  # third-party API: expects a key, costs money
            "label": "Grok (xAI)",
            "directions": ["tts", "stt"],
            "streaming": {"tts": True, "stt": True},
            "ready": bool(credentials.api_key()),
            "ready_detail": (
                "" if credentials.api_key()
                else "No xAI API key yet — paste one below (console.x.ai → API Keys)."
            ),
            "fields": [
                {
                    "key": "xai_api_key",
                    "kind": "secret",
                    "label": "xAI API key",
                    "required": True,
                    "hint": credentials.api_key_hint(),
                },
            ],
        },
        {
            "name": "local",
            "kind": "local",  # on-device: no key, picks a model instead
            "label": "Local (offline)",
            "directions": ["tts", "stt"],
            "streaming": {"tts": False, "stt": False},
            "ready": not _local_missing(),
            "ready_detail": _local_missing(),
            "fields": [
                {
                    "key": "stt_model",
                    "kind": "choice",
                    "label": "Whisper model",
                    "required": False,
                    "options": ["tiny", "base", "small", "medium", "large-v3"],
                    "value": str(
                        config.local_options().get("stt_model")
                        or config.DEFAULT_LOCAL_STT_MODEL
                    ),
                },
                _local_voice_field(),
            ],
        },
    ]


# The v1.0 voice pack ids, prefix = locale+gender (af = American female).
# Static on purpose: listing voices must not require the 340 MB model.
KOKORO_VOICES = [
    "af_bella", "af_heart", "af_nicole", "af_nova", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_michael", "am_onyx", "am_puck",
    "bf_alice", "bf_emma", "bf_isabella", "bm_daniel", "bm_george", "bm_lewis",
]


def _local_voice_field() -> dict[str, Any]:
    """The voice picker matches the engine: a free-text macOS voice name
    for `say`, a fixed choice of Kokoro ids otherwise."""
    value = str(config.local_options().get("tts_voice") or "")
    if _local_tts_engine() == "say":
        return {
            "key": "tts_voice",
            "kind": "text",
            "label": "macOS voice (empty = system default)",
            "required": False,
            "value": value,
        }
    return {
        "key": "tts_voice",
        "kind": "choice",
        "label": "Kokoro voice",
        "required": False,
        "options": KOKORO_VOICES,
        "value": value if value in KOKORO_VOICES else "af_sarah",
    }


def _local_tts_engine() -> str:
    return str(config.local_options().get("tts_engine") or "kokoro")


def _local_missing(*, tts: bool = True, stt: bool = True) -> str:
    """Empty string when local can work; otherwise what's missing and the fix.

    Checks match what actually runs: kokoro-onnx only while Kokoro is the
    chosen engine (say needs no package), so `ready` never lies about a
    dependency the first utterance would then trip over."""
    if stt and find_spec("faster_whisper") is None:
        return "faster-whisper is not installed — run: uv sync --extra local"
    if not tts:
        return ""
    if _local_tts_engine() == "say":
        if not shutil.which("say"):
            return "the macOS `say` command is missing on this system"
    elif find_spec("kokoro_onnx") is None:
        return "kokoro-onnx is not installed — run: uv sync --extra local"
    return ""
