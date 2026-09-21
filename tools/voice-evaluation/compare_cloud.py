"""Opt-in comparison: send only the five preserved hero utterances to xAI.

Without --allow-cloud, prints the bounded plan and performs no provider calls.
Never changes the running daemon or prints raw provider exceptions/credentials.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
TAKE = ROOT / 'tools/demo-recorder/takes/hero-v1'
CLIP_IDS = ('u1', 'u2', 'u3', 'u4', 'u5')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-cloud', action='store_true', help='Explicitly authorize five xAI recognition requests using the configured credential')
    args = parser.parse_args()
    if not args.allow_cloud:
        print('Plan only: compare hero-v1 u1–u5 against cached Whisper base and xAI Grok, alternating call order. Five cloud requests; no automatic retries. No audio sent.')
        return

    os.environ['HF_HUB_OFFLINE'] = '1'
    from noisy_studio import credentials
    from noisy_studio.providers.grok import GrokSTT
    from noisy_studio.providers.local import LocalSTT, models_present

    if not models_present(tts=False, options={'stt_model': 'base'}):
        raise SystemExit('Whisper base must already be cached. No cloud requests made.')
    if not credentials.api_key():
        raise SystemExit('No xAI credential configured. No cloud requests made.')

    local = LocalSTT({'stt_model': 'base'})
    local._load_model()
    cloud = GrokSTT()
    events = json.loads((TAKE / 'timeline.json').read_text())['events']
    results = {'kind': 'Five-clip batch comparison; not live streaming or a latency distribution', 'source': 'hero-v1/original.webm', 'language': 'en', 'runs': []}
    output = Path(__file__).with_name('cloud-results.json')
    with tempfile.TemporaryDirectory() as directory:
        for index, identity in enumerate(CLIP_IDS):
            start = next(e for e in events if e['type'] == 'user-start' and e['utterance'] == identity)
            end = next(e for e in events if e['type'] == 'user-end' and e['utterance'] == identity)
            duration = (end['atMs'] - start['atMs']) / 1000
            path = Path(directory) / f'{identity}.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start['atMs'] / 1000), '-i', str(TAKE / 'original.webm'), '-t', str(duration), '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(path)], check=True)
            audio = path.read_bytes()
            providers = [('whisper:base', local), ('grok:stt', cloud)]
            if index % 2:
                providers.reverse()
            for name, provider in providers:
                began = time.perf_counter()
                run = {'clip': identity, 'provider': name, 'duration_s': duration}
                try:
                    run['transcript'] = provider.transcribe(audio, 'en')
                except Exception as error:
                    # Error messages can include response bodies or headers. Retain type only.
                    run['error_type'] = type(error).__name__
                run['elapsed_ms'] = round((time.perf_counter() - began) * 1000)
                results['runs'].append(run)
                output.write_text(json.dumps(results, indent=2) + '\n')
            print(identity, 'completed', flush=True)
    print('Comparison saved. Inspect transcripts and failures before drawing conclusions.')


if __name__ == '__main__':
    main()
