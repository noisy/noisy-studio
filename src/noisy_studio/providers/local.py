"""Fully local voice — no API key, no cloud round-trip, no per-minute cost.

STT: faster-whisper (CTranslate2 Whisper), an optional dependency:

    uv sync --extra local        # or: pip install 'noisy-studio[local]'

The model (default "small", override in providers.json under
local.stt_model) downloads from Hugging Face on first use and is cached
by faster-whisper; every later transcription is offline. The model is
loaded once per process and reused — loading is the expensive part.

TTS: Kokoro by default — a small open TTS model (kokoro-onnx) with
natural voices that runs offline on CPU; the model files (~340 MB)
download once into the config dir. The macOS `say` engine remains the
zero-dependency fallback (local.tts_engine = "say"), because a garbled
but audible daemon beats a mute one. Other engines (Piper, and Nemotron
for STT) can slot behind the same seam later — see issue #37.

Streaming: neither direction streams yet (supports_streaming = False);
the daemon's batch paths carry local mode. Whisper partials are feasible
later by transcribing the growing buffer.
"""

import asyncio
import io
import json
import re
import tempfile
import threading
import wave
from collections.abc import Callable
from pathlib import Path

import httpx
import numpy as np

from noisy_studio.providers import config, downloads
from noisy_studio.providers.base import (
    STTError,
    STTStreamSession,
    SynthesizedAudio,
    TTSError,
)

_INSTALL_HINT = (
    "Local STT needs the optional faster-whisper dependency — install it "
    "with: uv sync --extra local (or pip install faster-whisper)."
)


class LocalSTT:
    name = "local"
    label = "local STT (whisper)"
    supports_streaming = False

    _model = None
    _model_name = ""
    _lock = threading.Lock()

    def __init__(self, options: dict | None = None):
        self.options = dict(config.local_options() if options is None else options)

    def _load_model(self):
        model_name = str(self.options.get("stt_model") or config.DEFAULT_LOCAL_STT_MODEL)
        with LocalSTT._lock:
            if LocalSTT._model is None or LocalSTT._model_name != model_name:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as error:
                    raise STTError(_INSTALL_HINT) from error
                key = f"whisper-{model_name}"
                label = f"Whisper model ({model_name})"
                # huggingface_hub exposes no byte-progress callback, so
                # whisper reports coarsely: downloading -> done.
                downloads.report(key, label, "downloading")
                try:
                    LocalSTT._model = WhisperModel(
                        model_name, device="auto", compute_type="auto",
                        local_files_only=_whisper_cached(model_name)
                    )
                except Exception as error:
                    downloads.report(key, label, "error", detail=str(error)[:200])
                    raise
                downloads.report(key, label, "done")
                LocalSTT._model_name = model_name
            return LocalSTT._model

    def transcribe(self, wav_bytes: bytes, language: str = "") -> str:
        model = self._load_model()
        samples = _wav_to_float32(wav_bytes)
        try:
            segments, _info = model.transcribe(
                samples,
                language=language or None,
                vad_filter=True,  # cheap guard against pure-noise utterances
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as error:
            raise STTError(f"Local transcription failed: {error}") from error

    def open_stream(
        self,
        sample_rate: int,
        language: str,
        on_partial: Callable[[str], None],
        smart_turn: float = 0.0,
        on_turn_end: Callable[[], None] | None = None,
    ) -> STTStreamSession | None:
        return None  # batch fallback

    def cost_usd(self, audio_seconds: float) -> float:
        return 0.0

    def streaming_cost_usd(self, audio_seconds: float) -> float:
        return 0.0


def _wav_to_float32(wav_bytes: bytes) -> np.ndarray:
    """Whisper wants mono float32 at 16 kHz — the daemon's native rate.

    The VAD already pulls devices to 16 kHz mono int16 (vad.py), so no
    resampling here; assert the assumption instead of silently degrading.
    """
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if rate != 16_000:
        # Linear resample in software — never touch the device's rate.
        target_length = int(len(samples) * 16_000 / rate)
        samples = np.interp(
            np.linspace(0.0, len(samples) - 1, target_length),
            np.arange(len(samples)),
            samples,
        ).astype(np.float32)
    return samples


_KOKORO_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
_KOKORO_MODEL_URL = f"{_KOKORO_RELEASE}/kokoro-v1.0.onnx"
_KOKORO_VOICES_URL = f"{_KOKORO_RELEASE}/voices-v1.0.bin"
DEFAULT_KOKORO_VOICE = "af_sarah"

_KOKORO_INSTALL_HINT = (
    "Local TTS needs the optional kokoro-onnx dependency — install it "
    "with: uv sync --extra local (or pip install kokoro-onnx). "
    'To use the built-in macOS voice instead, set local.tts_engine to "say".'
)


class _KokoroEngine:
    """kokoro-onnx behind a lock: loaded once per process, like the STT model."""

    _model = None
    _lock = threading.Lock()

    @classmethod
    def model(cls):
        with cls._lock:
            if cls._model is None:
                try:
                    from kokoro_onnx import Kokoro
                except ImportError as error:
                    raise TTSError(_KOKORO_INSTALL_HINT) from error
                model_path = _ensure_downloaded(_KOKORO_MODEL_URL, "kokoro-v1.0.onnx")
                voices_path = _ensure_downloaded(_KOKORO_VOICES_URL, "voices-v1.0.bin")
                cls._model = Kokoro(str(model_path), str(voices_path))
            return cls._model


_download_lock = threading.Lock()


def _ensure_downloaded(url: str, filename: str) -> Path:
    # Preparation and synthesis can request the same file concurrently.
    with _download_lock:
        return _download_file(url, filename)


def _download_file(url: str, filename: str) -> Path:
    """The model files land in the config dir once; every later run is
    offline. Progress goes to the downloads registry so the dashboard can
    draw a bar instead of the user staring at dead air."""
    from noisy_studio.config_dir import CONFIG_DIR

    label = f"Kokoro voice model ({filename})"
    target = CONFIG_DIR / "models" / "kokoro" / filename
    if target.exists() and target.stat().st_size > 0:
        size = target.stat().st_size
        downloads.report(filename, label, "done", size, size)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            done = 0
            downloads.report(filename, label, "downloading", 0, total)
            with partial.open("wb") as out:
                for chunk in response.iter_bytes():
                    out.write(chunk)
                    done += len(chunk)
                    downloads.report(filename, label, "downloading", done, total)
        if done == 0 or (total > 0 and done != total):
            raise OSError("The model download was incomplete. Retry the download.")
        partial.replace(target)
        downloads.report(filename, label, "done", done, total or done)
    except (httpx.HTTPError, OSError) as error:
        partial.unlink(missing_ok=True)
        downloads.report(filename, label, "error", detail=str(error)[:200])
        raise TTSError(f"Downloading the Kokoro model failed: {error}") from error
    return target


def _whisper_cached(model_name: str) -> bool:
    """Is the faster-whisper model already in the Hugging Face cache?
    Checked on disk (not via a loaded model) so a fresh daemon reports
    weights a previous run fetched."""
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    result = try_to_load_from_cache(
        f"Systran/faster-whisper-{model_name}", "model.bin"
    )
    if not isinstance(result, str):
        return False
    directory = Path(result).parent
    # Missing tokenizer data triggers a network fallback inside faster-whisper.
    return all((directory / filename).is_file() and (directory / filename).stat().st_size > 0
               for filename in ("model.bin", "config.json", "tokenizer.json"))


def models_present(tts: bool = True, stt: bool = True, options: dict | None = None) -> bool:
    """Every weight the CURRENT local configuration needs is on disk —
    the first utterance will not block on a download. Direction-aware:
    a mixed setup (say local TTS + cloud STT) needs only its own half."""
    from noisy_studio.config_dir import CONFIG_DIR

    options = config.local_options() if options is None else options
    engine = str(options.get("tts_engine") or "kokoro")
    if tts and engine != "say":
        kokoro_dir = CONFIG_DIR / "models" / "kokoro"
        for filename in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            target = kokoro_dir / filename
            if not (target.exists() and target.stat().st_size > 0):
                return False
    if stt:
        model_name = str(
            options.get("stt_model") or config.DEFAULT_LOCAL_STT_MODEL
        )
        return _whisper_cached(model_name)
    return True


def download_status() -> list[dict]:
    """What local-model weights exist, are arriving, or are missing —
    seeds the registry with on-disk facts so a fresh daemon reports
    'done' for files fetched by an earlier run."""
    from noisy_studio.config_dir import CONFIG_DIR

    kokoro_dir = CONFIG_DIR / "models" / "kokoro"
    known = {entry["name"] for entry in downloads.status()}
    for filename in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        if filename in known:
            continue
        target = kokoro_dir / filename
        label = f"Kokoro voice model ({filename})"
        if target.exists() and target.stat().st_size > 0:
            size = target.stat().st_size
            downloads.report(filename, label, "done", size, size)
        else:
            downloads.report(filename, label, "missing")
    model_name = str(
        config.local_options().get("stt_model") or config.DEFAULT_LOCAL_STT_MODEL
    )
    whisper_key = f"whisper-{model_name}"
    if whisper_key not in known:
        state = "done" if _whisper_cached(model_name) else "missing"
        downloads.report(whisper_key, f"Whisper model ({model_name})", state)
    return downloads.status()


def prefetch_models(*, tts: bool = True, stt: bool = True, options: dict | None = None) -> bool:
    """Start fetching every local weight in the background — called when
    the user switches an engine to local, so the first utterance finds
    the models already on disk."""
    options = dict(config.local_options() if options is None else options)
    engine = str(options.get("tts_engine") or "kokoro")
    targets = []
    if tts and engine != "say":
        targets.append(
            lambda: _ensure_downloaded(_KOKORO_MODEL_URL, "kokoro-v1.0.onnx")
        )
        targets.append(
            lambda: _ensure_downloaded(_KOKORO_VOICES_URL, "voices-v1.0.bin")
        )
    if stt:
        targets.append(lambda: LocalSTT(options)._load_model())
    return downloads.prefetch(targets)


class LocalTTS:
    name = "local"
    label = "local TTS (kokoro)"
    supports_streaming = False

    def __init__(self, options: dict | None = None):
        self.options = dict(config.local_options() if options is None else options)
        if self.options.get("voice_bindings") and self.options.get("tts_engine", "kokoro") == "kokoro":
            from noisy_studio.listener.state import VOICE_POOL
            from noisy_studio.providers.manifest import KOKORO_VOICES
            bindings = dict(self.options["voice_bindings"])
            for identity in VOICE_POOL:
                if bindings.get(identity) not in KOKORO_VOICES:
                    bindings[identity] = next((v for v in KOKORO_VOICES if v not in bindings.values()), KOKORO_VOICES[len(bindings) % len(KOKORO_VOICES)])
            self.options["voice_bindings"] = bindings
        self.cache_identity = "local:" + json.dumps(self.options, sort_keys=True)

    async def synthesize(
        self, text: str, voice_id: str, language: str, speed: float
    ) -> SynthesizedAudio:
        if language not in ("", "auto", "en", "en-US", "en-GB") and self.options.get("tts_engine", "kokoro") == "kokoro":
            raise TTSError("Kokoro currently supports English in this app. Choose another engine for this language.")
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        engine = str(self.options.get("tts_engine") or "kokoro")
        if engine == "say":
            return await self._synthesize_say(text, speed)
        return await asyncio.to_thread(self._synthesize_kokoro, text, voice_id, speed)

    def _synthesize_kokoro(
        self, text: str, voice_id: str, speed: float
    ) -> SynthesizedAudio:
        model = _KokoroEngine.model()
        voice = self._kokoro_voice(model, voice_id)
        try:
            samples, sample_rate = model.create(
                text, voice=voice, speed=max(0.5, min(2.0, speed))
            )
        except Exception as error:
            raise TTSError(f"Local TTS (kokoro) failed: {error}") from error
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(sample_rate)
            out.writeframes(pcm.tobytes())
        return SynthesizedAudio(buffer.getvalue(), "audio/wav", len(pcm) / sample_rate)

    def _kokoro_voice(self, model, voice_id: str) -> str:
        """The daemon's voice names are Grok's; map through config, or fall
        back to a fixed default so every agent still gets a stable voice."""
        known = set(model.get_voices())
        if voice_id in known:
            return voice_id
        mapped = self.options.get("voice_bindings", {}).get(voice_id)
        if mapped in known:
            return mapped
        configured = str(self.options.get("tts_voice") or "")
        if configured in known:
            return configured
        return DEFAULT_KOKORO_VOICE

    async def _synthesize_say(self, text: str, speed: float) -> SynthesizedAudio:
        voice = str(self.options.get("tts_voice") or "")
        # `say` rate is words per minute; ~180 wpm reads as speed 1.0.
        rate = max(90, min(360, int(180 * speed)))
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out:
            path = Path(out.name)
        command = ["say", "-o", str(path), "--data-format=LEI16@22050", "-r", str(rate)]
        if voice:
            command += ["-v", voice]
        command.append(text)
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise TTSError(
                    f"Local TTS (say) failed: {stderr.decode(errors='replace')[:300]}"
                )
            return SynthesizedAudio(path.read_bytes(), "audio/wav", 0.0)
        except FileNotFoundError as error:
            raise TTSError(
                "Local TTS needs the macOS `say` command; not found on this system."
            ) from error
        finally:
            path.unlink(missing_ok=True)

    async def speak_streaming(self, *args, **kwargs) -> None:
        raise TTSError("Local TTS does not stream — use the batch path.")

    async def list_voices(self) -> list[dict]:
        engine = str(self.options.get("tts_engine") or "kokoro")
        if engine != "say":
            from noisy_studio.providers.manifest import KOKORO_VOICES

            names = KOKORO_VOICES
            # Kokoro voice ids lead with a locale+gender prefix ("af_" =
            # American female); surface that as the language column.
            return [{"voice_id": name, "language": name.split("_")[0]} for name in names]
        try:
            result = await asyncio.create_subprocess_exec(
                "say", "-v", "?",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await result.communicate()
        except FileNotFoundError:
            return []
        voices = []
        for line in stdout.decode(errors="replace").splitlines():
            # "Samantha            en_US    # Hello! ..." — name may hold spaces.
            head = line.split("#")[0].rstrip()
            if not head:
                continue
            name, _, locale = head.rpartition(" ")
            voices.append({"voice_id": name.rstrip(), "language": locale})
        return voices

    def cost_usd(self, text_chars: int) -> float:
        return 0.0
