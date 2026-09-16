"""Voice-provider registry — the daemon's single door to TTS and STT.

Callers ask for `active_tts()` / `active_stt()` at the moment of use;
the selection in providers.json is re-read on every call, so switching
provider is a file write away, no restart (same contract as the API key
in credentials.py). Unknown names fail explicitly instead of silently sending speech to another service.
"""

from noisy_coding.providers import config
from noisy_coding.providers.base import (
    STTError,
    STTProvider,
    STTStreamSession,
    SynthesizedAudio,
    TTSError,
    TTSProvider,
)

__all__ = [
    "active_tts",
    "active_stt",
    "available",
    "catalog",
    "STTError",
    "TTSError",
    "STTProvider",
    "TTSProvider",
    "STTStreamSession",
    "SynthesizedAudio",
]


def _grok_tts() -> TTSProvider:
    from noisy_coding.providers.grok import GrokTTS

    return GrokTTS()


def _grok_stt() -> STTProvider:
    from noisy_coding.providers.grok import GrokSTT

    return GrokSTT()


def _local_tts() -> TTSProvider:
    from noisy_coding.providers.local import LocalTTS

    return LocalTTS()


def _local_stt() -> STTProvider:
    from noisy_coding.providers.local import LocalSTT

    return LocalSTT()


_TTS_FACTORIES = {"grok": _grok_tts, "local": _local_tts}
_STT_FACTORIES = {"grok": _grok_stt, "local": _local_stt}


def catalog() -> list[dict]:
    """Setup metadata for every provider — see providers/manifest.py."""
    from noisy_coding.providers.manifest import catalog as _catalog

    return _catalog()


def voice_ready() -> bool:
    """Can the daemon hear AND speak right now? True when the selected
    provider for each direction is ready (key present / installs in
    place). This — not "is an xAI key set" — is what the first-contact
    gate must ask, or a local-only user can never get past it."""
    entries = {entry["name"]: entry for entry in catalog()}
    tts = entries.get(config.tts_provider_name())
    stt = entries.get(config.stt_provider_name())
    if not (tts and tts["ready"] and stt and stt["ready"]):
        return False
    tts_local = config.tts_provider_name() == "local"
    stt_local = config.stt_provider_name() == "local"
    if tts_local or stt_local:
        # Installed is not enough: the WEIGHTS must be on disk, or the
        # gate would close while 340 MB is still in flight and the first
        # utterance would block on the download. Direction-aware — a
        # mixed setup only needs the weights for its local half.
        from noisy_coding.providers.local import models_present

        return models_present(tts=tts_local, stt=stt_local)
    return True


def available() -> dict[str, list[str]]:
    return {"tts": sorted(_TTS_FACTORIES), "stt": sorted(_STT_FACTORIES)}


def active_tts() -> TTSProvider:
    name = config.tts_provider_name()
    if name not in _TTS_FACTORIES:
        raise TTSError(f"Unknown speech provider: {name}. Choose an available engine in Settings.")
    factory = _TTS_FACTORIES[name]
    return factory()


def active_stt() -> STTProvider:
    name = config.stt_provider_name()
    if name not in _STT_FACTORIES:
        raise STTError(f"Unknown recognition provider: {name}. Choose an available engine in Settings.")
    factory = _STT_FACTORIES[name]
    return factory()


def stt_provider(name: str) -> STTProvider:
    """A named STT engine, regardless of what the daemon has active -
    for harnesses that compare engines side by side."""
    if name not in _STT_FACTORIES:
        raise KeyError(f"unknown STT provider {name!r}; have {sorted(_STT_FACTORIES)}")
    return _STT_FACTORIES[name]()
