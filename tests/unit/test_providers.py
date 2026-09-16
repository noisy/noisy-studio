"""The provider registry: selection, fallback, and the local provider."""

import io
import json
import wave

import numpy as np
import pytest

from noisy_coding import providers
from noisy_coding.providers import config
from noisy_coding.providers.base import STTError
from noisy_coding.providers.grok import GrokSTT, GrokTTS
from noisy_coding.providers.local import LocalSTT, LocalTTS, _wav_to_float32


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


def test_broken_file_falls_back_to_grok(providers_file):
    providers_file.write_text("{not json")
    assert isinstance(providers.active_tts(), GrokTTS)


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
    from noisy_coding.listener.stt import GrokSTTError
    from noisy_coding.listener.stt_stream import GrokStreamError
    from noisy_coding.tts import GrokTTSError
    from noisy_coding.tts_stream import GrokTTSStreamError

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
        "noisy_coding.providers.manifest._local_missing", lambda **kw: ""
    )
    monkeypatch.setattr(
        "noisy_coding.providers.local.models_present", lambda **kw: False
    )
    assert providers.voice_ready() is False
    monkeypatch.setattr(
        "noisy_coding.providers.local.models_present", lambda **kw: True
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
        "noisy_coding.providers.manifest._local_missing", lambda **kw: ""
    )
    monkeypatch.setattr(
        "noisy_coding.credentials.api_key", lambda: "xai-test-key"
    )
    kokoro_dir = tmp_path / "models" / "kokoro"
    kokoro_dir.mkdir(parents=True)
    for filename in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        (kokoro_dir / filename).write_bytes(b"weights")
    monkeypatch.setattr("noisy_coding.config_dir.CONFIG_DIR", tmp_path)
    monkeypatch.setattr(
        "noisy_coding.providers.local._whisper_cached",
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
    monkeypatch.setattr("noisy_coding.credentials.api_key", lambda: "test-key")
    monkeypatch.setattr("noisy_coding.providers.manifest.find_spec", lambda name: None if name == "faster_whisper" else object())
    monkeypatch.setattr("noisy_coding.providers.local.models_present", lambda **kw: True)
    assert providers.voice_ready() is True
