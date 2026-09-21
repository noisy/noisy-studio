"""Benchmark local voice models against Grok — cold and warm.

The question this answers: is local voice USABLE, in wall-clock terms,
on this machine? Run it from the repo root:

    uv run --no-config python tools/bench_voice.py

STT: a fixed ~10 s spoken WAV through faster-whisper (tiny/base/small,
large-v3 with --large) and through Grok batch STT. Model load ("cold
extra") is separated from inference; warm = second run in the same
process. Realtime factor = audio seconds / warm inference seconds
(higher is better; 1.0 = as fast as the audio plays).

TTS: a fixed two-sentence text through Kokoro, macOS `say`, and Grok
batch TTS. Cold = first call in the process (includes model load /
connection setup), warm = second call.

Grok numbers include the network on purpose — that is the honest
comparison the user experiences.
"""

import asyncio
import io
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

TTS_TEXT = (
    "The provider abstraction is done, and every engine now reports its "
    "own readiness. Switching between them is a single file write."
)
WHISPER_MODELS = ["tiny", "base", "small"]
if "--large" in sys.argv:
    WHISPER_MODELS.append("large-v3")


def make_speech_wav(seconds_target: float = 10.0) -> tuple[bytes, float]:
    """A ~10 s spoken WAV via `say` (real speech, not noise — VAD-friendly)."""
    text = (
        "This is a fixed benchmark utterance. It talks for roughly ten "
        "seconds about nothing in particular, so every model transcribes "
        "the exact same audio. The quick brown fox jumps over the lazy "
        "dog, twice on Sundays, and the daemon keeps listening."
    )
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out:
        path = Path(out.name)
    subprocess.run(
        ["say", "-o", str(path), "--data-format=LEI16@16000", text],
        check=True, capture_output=True,
    )
    wav_bytes = path.read_bytes()
    path.unlink()
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        duration = wav.getnframes() / wav.getframerate()
    return wav_bytes, duration


def bench_whisper(wav_bytes: bytes, duration: float) -> list[dict]:
    from faster_whisper import WhisperModel

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    rows = []
    for model_name in WHISPER_MODELS:
        t0 = time.monotonic()
        model = WhisperModel(model_name, device="auto", compute_type="auto")
        load_s = time.monotonic() - t0

        def run() -> float:
            t = time.monotonic()
            segments, _ = model.transcribe(samples, language="en")
            list(segments)  # generator — consume it or nothing runs
            return time.monotonic() - t

        first = run()
        warm = min(run() for _ in range(2))
        rows.append({
            "name": f"whisper {model_name} (local)",
            "cold_ms": (load_s + first) * 1000,
            "warm_ms": warm * 1000,
            "rtf": duration / warm,
        })
        del model
    return rows


def bench_grok_stt(wav_bytes: bytes, duration: float) -> list[dict]:
    from noisy_studio.listener import stt

    def run() -> float:
        t = time.monotonic()
        stt.transcribe(wav_bytes, "en")
        return time.monotonic() - t

    first = run()
    warm = min(run() for _ in range(2))
    return [{
        "name": "Grok STT (cloud)",
        "cold_ms": first * 1000,
        "warm_ms": warm * 1000,
        "rtf": duration / warm,
    }]


def bench_tts() -> list[dict]:
    rows = []

    # Kokoro
    from noisy_studio.providers.local import LocalTTS

    local = LocalTTS()

    def run_kokoro() -> float:
        t = time.monotonic()
        local._synthesize_kokoro(TTS_TEXT, "af_sarah", 1.0)
        return time.monotonic() - t

    first = run_kokoro()
    warm = min(run_kokoro() for _ in range(2))
    rows.append({"name": "Kokoro (local)", "cold_ms": first * 1000, "warm_ms": warm * 1000})

    # macOS say
    def run_say() -> float:
        t = time.monotonic()
        asyncio.run(local._synthesize_say(TTS_TEXT, 1.0))
        return time.monotonic() - t

    first = run_say()
    warm = min(run_say() for _ in range(2))
    rows.append({"name": "macOS say (local)", "cold_ms": first * 1000, "warm_ms": warm * 1000})

    # Grok
    from noisy_studio import tts as grok_tts

    def run_grok() -> float:
        t = time.monotonic()
        asyncio.run(grok_tts.synthesize(TTS_TEXT, "eve", "en", 1.0))
        return time.monotonic() - t

    first = run_grok()
    warm = min(run_grok() for _ in range(2))
    rows.append({"name": "Grok TTS (cloud)", "cold_ms": first * 1000, "warm_ms": warm * 1000})
    return rows


def table(title: str, rows: list[dict], rtf: bool) -> str:
    out = [f"\n### {title}\n"]
    header = "| engine | cold ms | warm ms |" + (" realtime factor |" if rtf else "")
    out.append(header)
    out.append("|---|---|---|" + ("---|" if rtf else ""))
    for r in rows:
        line = f"| {r['name']} | {r['cold_ms']:.0f} | {r['warm_ms']:.0f} |"
        if rtf:
            line += f" {r['rtf']:.1f}x |"
        out.append(line)
    return "\n".join(out)


def main() -> None:
    wav_bytes, duration = make_speech_wav()
    print(f"benchmark audio: {duration:.1f}s of speech, TTS text: {len(TTS_TEXT)} chars")

    stt_rows = bench_whisper(wav_bytes, duration)
    try:
        stt_rows += bench_grok_stt(wav_bytes, duration)
    except Exception as error:
        print(f"(Grok STT skipped: {error})")
    print(table(f"STT — transcribe {duration:.1f}s of speech", stt_rows, rtf=True))

    tts_rows = bench_tts()
    print(table(f"TTS — synthesize {len(TTS_TEXT)} chars", tts_rows, rtf=False))


if __name__ == "__main__":
    main()
