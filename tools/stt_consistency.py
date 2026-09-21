#!/usr/bin/env python3
"""STT consistency test: same audio, N transcriptions - how much do they differ?

Born on stream day 4: transcripts of the same-sounding phrases kept coming
out different, and the suspect list had two names - the microphone pipeline
(different bytes every time) and the STT API (different words for the SAME
bytes). This harness settles it by replaying identical WAV bytes.

Usage:
    .venv/bin/python tools/stt_consistency.py [WAV ...] [--runs 10]
                                              [--provider grok|local]

With no WAV arguments it picks the 3 newest recordings from the daemon's
utterance archive (CONFIG_DIR/utterance_audio - the daemon saves every
batch-transcribed utterance there).

Output per file: every distinct transcript with its count, and a consistency
score (mean pairwise similarity, difflib ratio 0..1). A score of 1.0 means
the engine is deterministic on this audio; anything under ~0.95 is the API
changing its mind about identical input.
"""
import argparse
import difflib
import time
import wave
import itertools
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from noisy_studio import providers  # noqa: E402
from noisy_studio.config_dir import CONFIG_DIR  # noqa: E402


def newest_utterances(count: int) -> list[Path]:
    archive = CONFIG_DIR / "utterance_audio"
    return sorted(archive.glob("*.wav"))[-count:]


def transcribe_live(provider, wav_path: Path, language: str) -> str:
    """Replay a WAV through the STREAMING path, paced like a microphone:
    30 ms frames, then finish(). Same bytes, other pipeline."""
    with wave.open(str(wav_path), "rb") as wav:
        rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())
    session = provider.open_stream(rate, language, lambda text: None)
    if session is None:
        return "<ERROR: engine has no streaming path>"
    frame_bytes = int(rate * 0.03) * 2  # 30 ms of int16 mono
    for i in range(0, len(pcm), frame_bytes):
        session.send(pcm[i:i + frame_bytes])
        time.sleep(0.005)  # gentle pacing; full realtime would take ages x runs
    return session.finish()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def test_file(path: Path, runs: int, provider_name: str, language: str,
              mode: str = "batch") -> float:
    provider = (
        providers.stt_provider(provider_name) if provider_name else providers.active_stt()
    )
    print(f"\n=== {path.name} · {runs} runs · engine: {provider.label} · path: {mode} ===")
    wav_bytes = path.read_bytes()
    transcripts: list[str] = []
    for i in range(runs):
        try:
            if mode == "live":
                text = transcribe_live(provider, path, language)
            else:
                text = provider.transcribe(wav_bytes, language)
        except Exception as error:  # noqa: BLE001 - report, keep testing
            text = f"<ERROR: {error}>"
        transcripts.append(text)
        print(f"  run {i + 1:2d}: {text}")

    distinct: dict[str, int] = {}
    for t in transcripts:
        distinct[t] = distinct.get(t, 0) + 1
    print(f"  -> {len(distinct)} distinct transcript(s)")
    reference = max(distinct, key=lambda t: distinct[t])
    for text, count in sorted(distinct.items(), key=lambda kv: -kv[1]):
        print(f"     {count:2d}x  {text}")
        if text != reference:
            # Show WHAT changed, not just that it did - word-level diff
            # against the most common transcript.
            delta = [
                f"[-{' '.join(reference.split()[a1:a2])}|+{' '.join(text.split()[b1:b2])}]"
                for op, a1, a2, b1, b2 in difflib.SequenceMatcher(
                    None, reference.lower().split(), text.lower().split()
                ).get_opcodes()
                if op != "equal"
            ]
            print(f"          diff vs most common: {' '.join(delta)}")

    if len(transcripts) < 2:
        return 1.0
    pairs = [similarity(a, b) for a, b in itertools.combinations(transcripts, 2)]
    score = statistics.mean(pairs)
    print(f"  consistency score: {score:.3f} "
          f"(min pair {min(pairs):.3f})")
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wavs", nargs="*", type=Path)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--provider", default="",
                        help="grok | local (default: the daemon's active engine)")
    parser.add_argument("--language", default="")
    parser.add_argument("--path", default="batch",
                        choices=["batch", "live", "both"],
                        help="which pipeline to replay through - the batch "
                             "endpoint, the streaming one, or both on the "
                             "same recordings")
    parser.add_argument("--threshold", type=float, default=0.90,
                        help="minimum acceptable consistency score (exit 1 "
                             "below it) - punctuation and case wobble is "
                             "normal, changed WORDS are not")
    args = parser.parse_args()

    files = args.wavs or newest_utterances(3)
    if not files:
        sys.exit("No WAV files given and the utterance archive is empty - "
                 "speak to the daemon first, then rerun.")

    modes = ["batch", "live"] if args.path == "both" else [args.path]
    scores = [
        test_file(f, args.runs, args.provider, args.language, mode)
        for f in files for mode in modes
    ]
    print(f"\nOVERALL: mean consistency {statistics.mean(scores):.3f} "
          f"across {len(files)} file(s), {args.runs} runs each.")
    print("1.000 = deterministic; below ~0.95 = the engine returns different "
          "words for identical bytes.")
    overall = statistics.mean(scores)
    if overall < args.threshold:
        sys.exit(f"FAIL: consistency {overall:.3f} below threshold {args.threshold}")
    print(f"PASS (threshold {args.threshold})")


if __name__ == "__main__":
    main()
