"""The provider registry: selection, fallback, and the local provider."""

import io
import json
import wave

import numpy as np
import pytest

from noisy_studio import providers
from noisy_studio.providers import config
from noisy_studio.providers.base import STTError
from noisy_studio.providers.grok import GrokSTT, GrokTTS
from noisy_studio.providers.local import LocalSTT, LocalTTS, _wav_to_float32


@pytest.fixture
def providers_file(tmp_path, monkeypatch):
    path = tmp_path / "providers.json"
    monkeypatch.setattr(config, "PROVIDERS_FILE", path)
    return path


def test_defaults_to_grok(providers_file):
    assert isinstance(providers.active_tts(), GrokTTS)
    assert isinstance(providers.active_stt(), GrokSTT)


def test_selection_is_read_per_call(providers_file):
    """Switching provider is a file write — no restart, no caching."""
    assert isinstance(providers.active_stt(), GrokSTT)
    providers_file.write_text(json.dumps({"stt": "local", "tts": "local"}))
    assert isinstance(providers.active_stt(), LocalSTT)
    assert isinstance(providers.active_tts(), LocalTTS)


def test_unknown_provider_never_silently_sends_speech_to_grok(providers_file):
    providers_file.write_text(json.dumps({"tts": "no-such-engine"}))
    with pytest.raises(providers.TTSError, match="Unknown speech provider"):
        providers.active_tts()


@pytest.mark.parametrize('contents', [
    '{not json', '[]', '{"stt":null}', '{"providers":[]}',
    '{"local":{"tts_engine":[]}}', '{"local":{"voice_bindings":[]}}',
    '{"providers":{"grok":{"voice_bindings_by_engine":{"grok:tts":[]}}}}',
])
def test_invalid_saved_settings_never_fall_back_or_get_overwritten(providers_file, contents):
    providers_file.write_text(contents)
    with pytest.raises(providers.TTSError, match="No fallback engine"):
        providers.active_tts()
    with pytest.raises(providers.STTError, match="No fallback engine"):
        providers.active_stt()
    with pytest.raises(config.ConfigurationError):
        config.save(tts='grok')
    assert providers_file.read_text() == contents


def test_save_merges_local_options(providers_file):
    config.save(stt="local", stt_model="base")
    config.save(tts="local")
    data = json.loads(providers_file.read_text())
    assert data == {"stt": "local", "tts": "local", "local": {"stt_model": "base"}}


def test_local_provider_is_free(providers_file):
    assert LocalSTT().cost_usd(60.0) == 0.0
    assert LocalSTT().streaming_cost_usd(60.0) == 0.0
    assert LocalTTS().cost_usd(1000) == 0.0


def test_local_stt_does_not_stream(providers_file):
    assert LocalSTT().open_stream(16_000, "", lambda text: None) is None


def test_local_stt_without_dependency_raises_install_hint(
    providers_file, monkeypatch
):
    monkeypatch.setattr(
        "builtins.__import__",
        _blocking_import("faster_whisper"),
    )
    LocalSTT._model = None  # never reuse a model another test loaded
    with pytest.raises(STTError, match="faster-whisper"):
        LocalSTT().transcribe(_silence_wav())


def _blocking_import(blocked: str):
    real_import = __import__

    def guarded(name, *args, **kwargs):
        if name == blocked:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    return guarded


def _silence_wav(rate: int = 16_000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(np.zeros(rate, dtype=np.int16).tobytes())
    return buffer.getvalue()


def test_wav_decoding_native_rate():
    samples = _wav_to_float32(_silence_wav())
    assert samples.dtype == np.float32
    assert len(samples) == 16_000


def test_wav_decoding_resamples_other_rates():
    samples = _wav_to_float32(_silence_wav(rate=44_100))
    assert len(samples) == 16_000  # one second stays one second


def test_grok_errors_are_provider_errors():
    """Callers catch providers.STTError/TTSError — Grok's must qualify."""
    from noisy_studio.listener.stt import GrokSTTError
    from noisy_studio.listener.stt_stream import GrokStreamError
    from noisy_studio.tts import GrokTTSError
    from noisy_studio.tts_stream import GrokTTSStreamError

    assert issubclass(GrokSTTError, providers.STTError)
    assert issubclass(GrokStreamError, providers.STTError)
    assert issubclass(GrokTTSError, providers.TTSError)
    assert issubclass(GrokTTSStreamError, providers.TTSError)


def test_catalog_names_match_registry(providers_file):
    names = {entry["name"] for entry in providers.catalog()}
    assert names == set(providers.available()["tts"])


def test_voice_ready_requires_local_weights_on_disk(providers_file, monkeypatch):
    """The gate must stay open while the 340 MB is still in flight: an
    installed-but-not-downloaded local setup is NOT ready (PR #47 round 2)."""
    providers_file.write_text(json.dumps({"stt": "local", "tts": "local"}))
    monkeypatch.setattr(
        "noisy_studio.providers.builtin_selection.find_spec", lambda name: object()
    )
    monkeypatch.setattr(
        "noisy_studio.providers.local.models_present", lambda **kw: False
    )
    assert providers.voice_ready() is False
    monkeypatch.setattr(
        "noisy_studio.providers.local.models_present", lambda **kw: True
    )
    assert providers.voice_ready() is True


def test_voice_ready_checks_only_the_local_direction(
    providers_file, monkeypatch, tmp_path
):
    """Mixed setup: tts=local(kokoro weights present) + stt=grok(key set)
    must pass the gate without the whisper cache (PR #47 round 3)."""
    providers_file.write_text(
        json.dumps({"tts": "local", "stt": "grok", "local": {}})
    )
    monkeypatch.setattr(
        "noisy_studio.providers.builtin_selection.find_spec", lambda name: object()
    )
    monkeypatch.setattr(
        "noisy_studio.credentials.api_key", lambda: "xai-test-key"
    )
    kokoro_dir = tmp_path / "models" / "kokoro"
    kokoro_dir.mkdir(parents=True)
    for filename in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        (kokoro_dir / filename).write_bytes(b"weights")
    monkeypatch.setattr("noisy_studio.config_dir.CONFIG_DIR", tmp_path)
    monkeypatch.setattr(
        "noisy_studio.providers.local._whisper_cached",
        lambda model: (_ for _ in ()).throw(AssertionError("STT is grok — must not be checked")),
    )
    assert providers.voice_ready() is True


def test_catalog_survives_repeated_calls(providers_file):
    """Regression: the metadata submodule import must never shadow the
    package-level catalog() function (it did, when both were named
    'catalog' — the second HTTP GET /providers then 500'd)."""
    assert providers.catalog() == providers.catalog()
    assert callable(providers.catalog)


def test_mixed_setup_does_not_require_unused_recognition_dependency(providers_file, monkeypatch):
    providers_file.write_text(json.dumps({"tts": "local", "stt": "grok"}))
    monkeypatch.setattr("noisy_studio.credentials.api_key", lambda: "test-key")
    monkeypatch.setattr("noisy_studio.providers.builtin_selection.find_spec", lambda name: None if name == "faster_whisper" else object())
    monkeypatch.setattr("noisy_studio.providers.local.models_present", lambda **kw: True)
    assert providers.voice_ready() is True


@pytest.mark.parametrize('provider,preferred,expected', [
    ('grok', 'live', 'live'), ('grok', 'batch', 'batch'),
    ('local', 'live', 'batch'), ('local', 'batch', 'batch'),
    ('unknown', 'live', 'unavailable'),
])
@pytest.mark.parametrize('direction', ['stt', 'tts'])
def test_effective_mode_reflects_engine_capabilities(providers_file, monkeypatch, direction, provider, preferred, expected):
    monkeypatch.setattr("noisy_studio.tts_stream.streaming_available", lambda: True)
    providers_file.write_text(json.dumps({direction: provider}))
    assert providers.effective_mode(direction, preferred) == expected


def test_third_provider_receives_its_own_options_without_overwriting_local_settings(providers_file, monkeypatch):
    config.save(stt="local", stt_model="small", voice_bindings={"lux": "af_sarah"})
    config.save_selection("tts", "example", {"model": "voice-v2", "voice_bindings": {"lux": "voice-a"}})
    received = []
    monkeypatch.setitem(providers._TTS_FACTORIES, "example", lambda options: received.append(options))

    providers.active_tts()

    assert {
        "factory_options": received,
        "local_options": config.local_options(),
        "recognition": config.stt_provider_name(),
    } == {
        "factory_options": [{"model": "voice-v2", "voice_bindings": {"lux": "voice-a"}}],
        "local_options": {"stt_model": "small", "voice_bindings": {"lux": "af_sarah"}},
        "recognition": "local",
    }


def test_switching_provider_preserves_its_settings_for_return(providers_file):
    config.save_selection("tts", "example", {"model": "voice-v2"})
    config.save_selection("tts", "grok", {})
    config.save_selection("tts", "example", {})

    assert config.provider_options("example") == {"model": "voice-v2"}


@pytest.mark.asyncio
async def test_grok_voice_bindings_are_frozen_and_used_for_synthesis(providers_file, monkeypatch):
    from unittest.mock import AsyncMock
    from noisy_studio.providers.base import SynthesizedAudio
    synthesize = AsyncMock(return_value=SynthesizedAudio(b'audio', 'audio/mpeg', 1))
    monkeypatch.setattr('noisy_studio.providers.grok.tts.synthesize', synthesize)
    config.save_selection('tts', 'grok', {'voice_bindings': {'lux': 'rex'}})
    prepared = providers.active_tts()
    config.save_selection('tts', 'grok', {'voice_bindings': {'lux': 'luna'}})

    await prepared.synthesize('Hello', 'lux', 'en', 1)

    synthesize.assert_awaited_once_with('Hello', 'rex', 'en', 1)
    assert prepared.cache_identity != providers.active_tts().cache_identity


def test_kokoro_replaces_bindings_from_another_local_engine():
    from noisy_studio.providers.manifest import KOKORO_VOICES
    provider = LocalTTS({'tts_engine':'kokoro', 'voice_bindings':{'lux':'system', 'rex':'am_adam'}})
    assert provider.options['voice_bindings']['lux'] in KOKORO_VOICES
    assert provider.options['voice_bindings']['rex'] == 'am_adam'
