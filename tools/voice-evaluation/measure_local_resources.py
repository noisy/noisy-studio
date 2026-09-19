"""Measure cached Whisper models in separate offline processes; preserve demo originals."""
import argparse
import importlib.metadata
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Set before importing Hugging Face or the provider; no accidental downloads.
os.environ['HF_HUB_OFFLINE'] = '1'
from noisy_coding.providers.local import LocalSTT, models_present

ROOT = Path(__file__).resolve().parents[2]
TAKE = ROOT / 'tools/demo-recorder/takes/hero-v1'
WARM_REPETITIONS = 20


def measure(model, wav):
    if not models_present(tts=False, options={'stt_model': model}):
        return {'model': model, 'skipped': 'not fully cached'}
    provider = LocalSTT({'stt_model': model})
    started = time.perf_counter()
    provider._load_model()
    load_ms = (time.perf_counter() - started) * 1000
    audio = Path(wav).read_bytes()
    started = time.perf_counter()
    transcript = provider.transcribe(audio, 'en')
    first_ms = (time.perf_counter() - started) * 1000
    times = []
    for _ in range(WARM_REPETITIONS):
        started = time.perf_counter()
        provider.transcribe(audio, 'en')
        times.append((time.perf_counter() - started) * 1000)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_bytes = peak if sys.platform == 'darwin' else peak * 1024
    from huggingface_hub import try_to_load_from_cache
    model_file = Path(try_to_load_from_cache(f'Systran/faster-whisper-{model}', 'model.bin'))
    cached_bytes = sum(path.stat().st_size for path in model_file.parent.iterdir() if path.is_file())
    return dict(model=model, process_cold_load_ms=round(load_ms), first_inference_ms=round(first_ms),
                warm_runs=WARM_REPETITIONS, warm_median_ms=round(statistics.median(times)),
                warm_p95_ms=round(sorted(times)[18]), peak_process_rss_bytes=peak_bytes,
                cached_snapshot_bytes=cached_bytes, transcript=transcript)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['tiny', 'base', 'small'])
    parser.add_argument('--wav')
    args = parser.parse_args()
    if args.model:
        print(json.dumps(measure(args.model, args.wav)))
        return
    events = json.loads((TAKE / 'timeline.json').read_text())['events']
    start = next(event for event in events if event['type'] == 'user-start')
    end = next(event for event in events if event['type'] == 'user-end' and event['utterance'] == start['utterance'])
    duration = (end['atMs'] - start['atMs']) / 1000
    result = {
        'scope': 'One English human utterance with Polish accent. Offline batch inference, not end-to-end latency or quality ranking.',
        'method': 'Fresh process per model. OS disk cache is not flushed. RSS includes Python and runtime, not just model weights.',
        'platform': platform.platform(), 'python': platform.python_version(),
        'versions': {name: importlib.metadata.version(name) for name in ['faster-whisper', 'ctranslate2', 'numpy']},
        'clip': start['utterance'], 'audio_seconds': duration, 'runs': [],
    }
    with tempfile.TemporaryDirectory() as directory:
        wav = Path(directory) / 'sample.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start['atMs']/1000), '-i', str(TAKE/'original.webm'), '-t', str(duration), '-ar', '16000', '-ac', '1', str(wav)], check=True)
        for model in ['tiny', 'base', 'small']:
            completed = subprocess.run([sys.executable, __file__, '--model', model, '--wav', str(wav)], check=True, capture_output=True, text=True)
            result['runs'].append(json.loads(completed.stdout))
            print(f'{model}: measured in isolated process', flush=True)
    (Path(__file__).parent / 'local-resource-results.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
