"""Deterministic noise stress probe of cached models, preserving source recordings.

Script references are not verbatim ground truth: report transcript changes rather
than presenting word-error rates against potentially paraphrased prompts.
"""
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import wave

import numpy as np

os.environ['HF_HUB_OFFLINE'] = '1'
from noisy_studio.providers.local import LocalSTT, models_present

ROOT = Path(__file__).resolve().parents[2]
TAKE = ROOT / 'tools/demo-recorder/takes/hero-v1'
NOISE_SEED = 20260918
SAMPLE_RATE = 16000


def noisy_wav(audio: bytes, snr_db: int | None) -> bytes:
    if snr_db is None:
        return audio
    with wave.open(io.BytesIO(audio)) as source:
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float64)
    # Whole-clip RMS includes intentional pauses; this is not speech-active SNR.
    noise = np.random.default_rng(NOISE_SEED).normal(size=samples.size)
    noise *= np.sqrt(np.mean(samples ** 2)) / (10 ** (snr_db / 20) * np.sqrt(np.mean(noise ** 2)))
    mixed = samples + noise
    # Scale the whole mixture equally to avoid clipping and preserve its SNR.
    mixed *= min(1.0, 32767 / max(1.0, float(np.max(np.abs(mixed)))))
    output = io.BytesIO()
    with wave.open(output, 'wb') as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(SAMPLE_RATE)
        target.writeframes(mixed.astype('<i2').tobytes())
    return output.getvalue()


def main():
    events = json.loads((TAKE / 'timeline.json').read_text())['events']
    results = {
        'kind': 'Offline synthetic white-noise stress probe; not real-world noise or live latency',
        'seed': NOISE_SEED,
        'snr_definition': 'Whole-clip RMS including pauses; Gaussian white noise',
        'reference_limit': 'Prompts describe intended speech, not verified verbatim ground truth',
        'runs': [],
    }
    with tempfile.TemporaryDirectory() as directory:
        clips = []
        for event in events:
            if event['type'] != 'user-start':
                continue
            end = next(e for e in events if e['type'] == 'user-end' and e['utterance'] == event['utterance'])
            path = Path(directory) / (event['utterance'] + '.wav')
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(event['atMs'] / 1000), '-i', str(TAKE / 'original.webm'), '-t', str((end['atMs'] - event['atMs']) / 1000), '-ar', str(SAMPLE_RATE), '-ac', '1', '-c:a', 'pcm_s16le', str(path)], check=True)
            clips.append((event['utterance'], event['prompt'], path.read_bytes()))
        for model in ('tiny', 'base', 'small'):
            if not models_present(tts=False, options={'stt_model': model}):
                results['runs'].append({'model': model, 'skipped': 'not cached'})
                continue
            provider = LocalSTT({'stt_model': model})
            provider._load_model()
            outputs = []
            for identity, prompt, audio in clips:
                for snr in (None, 20, 10):
                    sample = noisy_wav(audio, snr)
                    start = time.perf_counter()
                    transcript = provider.transcribe(sample, 'en')
                    outputs.append({'clip': identity, 'script_reference': prompt, 'snr_db': snr, 'transcript': transcript, 'inference_ms': round((time.perf_counter() - start) * 1000)})
            results['runs'].append({'model': model, 'clips': outputs})
            (ROOT / 'tools/voice-evaluation/noise-results.json').write_text(json.dumps(results, indent=2) + '\n')
            print(model, 'completed', flush=True)


if __name__ == '__main__':
    main()
