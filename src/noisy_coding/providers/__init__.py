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


def _grok_tts(options=None) -> TTSProvider:
    from noisy_coding.providers.grok import GrokTTS

    return GrokTTS()


def _grok_stt(options=None) -> STTProvider:
    from noisy_coding.providers.grok import GrokSTT

    return GrokSTT()


def _local_tts(options=None) -> TTSProvider:
    from noisy_coding.providers.local import LocalTTS

    return LocalTTS(options)


def _local_stt(options=None) -> STTProvider:
    from noisy_coding.providers.local import LocalSTT

    return LocalSTT(options)


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
    from noisy_coding import credentials
    from noisy_coding.providers.local import models_present
    from noisy_coding.providers.manifest import _local_missing

    names = (config.tts_provider_name(), config.stt_provider_name())
    if names[0] not in _TTS_FACTORIES or names[1] not in _STT_FACTORIES:
        return False
    if "grok" in names and not credentials.api_key():
        return False
    tts_local, stt_local = names[0] == "local", names[1] == "local"
    if tts_local or stt_local:
        return not _local_missing(tts=tts_local, stt=stt_local) and models_present(
            tts=tts_local, stt=stt_local
        )
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


def stt_provider(name: str, options: dict | None = None) -> STTProvider:
    """A named STT engine, regardless of what the daemon has active -
    for harnesses that compare engines side by side."""
    if name not in _STT_FACTORIES:
        raise KeyError(f"unknown STT provider {name!r}; have {sorted(_STT_FACTORIES)}")
    return _STT_FACTORIES[name](options)


def tts_provider(name: str, options: dict | None = None) -> TTSProvider:
    if name not in _TTS_FACTORIES:
        raise TTSError(f"Unknown speech provider: {name}")
    return _TTS_FACTORIES[name](options)
