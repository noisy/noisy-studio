"""Verify cached recognition with Hugging Face networking disabled."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

# Set before importing huggingface_hub through the provider.
os.environ['HF_HUB_OFFLINE'] = '1'
from noisy_studio.providers.local import LocalSTT, models_present

ROOT = Path(__file__).resolve().parents[2]
TAKE = ROOT / 'tools/demo-recorder/takes/hero-v1'


def main():
    if not models_present(tts=False, options={'stt_model': 'base'}):
        raise SystemExit('Whisper base cache is incomplete; this verification never downloads it.')
    events = json.loads((TAKE / 'timeline.json').read_text())['events']
    start = next(event for event in events if event['type'] == 'user-start')
    end = next(event for event in events if event['type'] == 'user-end' and event['utterance'] == start['utterance'])
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'sample.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start['atMs']/1000), '-i', str(TAKE/'original.webm'), '-t', str((end['atMs']-start['atMs'])/1000), '-ar', '16000', '-ac', '1', str(path)], check=True)
        text = LocalSTT({'stt_model':'base'}).transcribe(path.read_bytes(), 'en')
    if not text.strip():
        raise RuntimeError('Offline recognition returned no text')
    result = {'model':'Whisper base', 'hub_offline':True, 'clip':start['utterance'], 'transcript':text}
    Path(__file__).with_name('offline-recognition-results.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Whisper base recognized the preserved recording with Hugging Face networking disabled.')


if __name__ == '__main__':
    main()
