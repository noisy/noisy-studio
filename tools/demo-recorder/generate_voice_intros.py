"""Generate the website voice introductions using the configured xAI provider.

Requires explicit permission to access configured credentials during a stream.
Run from the repo root: PYTHONPATH=src .venv/bin/python tools/demo-recorder/generate_voice_intros.py
Existing clips are skipped; remove a clip explicitly to regenerate it.
"""
import asyncio
import json
from pathlib import Path
from noisy_studio.tts import synthesize

async def main():
    folder = Path(__file__).resolve().parents[2] / 'website/src/assets/voice-intros'
    for voice in json.loads((folder / 'scripts.json').read_text()):
        output = folder / f'{voice["name"].lower()}.mp3'
        if output.exists():
            continue
        try:
            audio = await synthesize(voice['text'], voice['name'].lower(), 'en', 1.0)
            output.write_bytes(audio.audio)
            print(f'Created {output.name}', flush=True)
        except Exception:
            raise SystemExit(f'Generation failed for {voice["name"]}; provider details withheld.') from None

if __name__ == '__main__':
    asyncio.run(main())
