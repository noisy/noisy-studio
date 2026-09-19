"""Offline exploratory comparison using preserved hero speech; no live config writes."""
import json
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from noisy_coding.providers.local import LocalSTT, models_present

ROOT = Path(__file__).resolve().parents[2]
TAKE = ROOT / 'tools/demo-recorder/takes/hero-v1'


def main():
    timeline = json.loads((TAKE / 'timeline.json').read_text())
    events = timeline['events']
    results = {'kind': 'exploratory batch recognition; not end-to-end live latency', 'runs': []}
    with tempfile.TemporaryDirectory() as directory:
        clips = []
        for event in events:
            if event['type'] != 'user-start':
                continue
            end = next(e for e in events if e['type'] == 'user-end' and e['utterance'] == event['utterance'])
            path = Path(directory) / (event['utterance'] + '.wav')
            duration = (end['atMs'] - event['atMs']) / 1000
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(event['atMs']/1000), '-i', str(TAKE/'original.webm'), '-t', str(duration), '-ar', '16000', '-ac', '1', str(path)], check=True)
            clips.append((event['utterance'], event['prompt'], duration, path.read_bytes()))
        for model in ('tiny', 'base', 'small'):
            if not models_present(tts=False, options={'stt_model': model}):
                results['runs'].append({'model': model, 'skipped': 'not cached'})
                continue
            provider = LocalSTT({'stt_model': model})
            start = time.perf_counter()
            provider._load_model()
            load_ms = (time.perf_counter()-start)*1000
            outputs = []
            for identity, reference, duration, audio in clips:
                start = time.perf_counter()
                text = provider.transcribe(audio, 'en')
                outputs.append({'clip': identity, 'script_reference': reference, 'duration_s': duration, 'transcript': text, 'inference_ms': round((time.perf_counter()-start)*1000)})
            timings = []
            for _ in range(20):
                start = time.perf_counter()
                provider.transcribe(clips[0][3], 'en')
                timings.append((time.perf_counter()-start)*1000)
            results['runs'].append({'model': model, 'load_ms': round(load_ms), 'sample_count':len(timings), 'warm_median_ms':round(statistics.median(timings)), 'warm_p95_ms':round(sorted(timings)[18]), 'clips': outputs})
            (ROOT/'tools/voice-evaluation/cached-results.json').write_text(json.dumps(results,indent=2))
            print(model, 'completed', flush=True)


if __name__ == '__main__':
    main()
