"""Exercise cached local voice generation without changing daemon settings."""
import asyncio
import io
import json
import time
import wave
from pathlib import Path

from noisy_studio.providers.local import LocalTTS, models_present


async def main():
    options = {'tts_engine': 'kokoro', 'voice_bindings': {'lux': 'af_sarah', 'rex': 'am_adam', 'luna': 'bf_emma'}}
    if not models_present(tts=True, stt=False, options=options):
        raise SystemExit('Prepare Kokoro first; this verification does not download models.')
    engine = LocalTTS(options)
    results = []
    for identity in options['voice_bindings']:
        started = time.perf_counter()
        audio = await engine.synthesize('The search ignores capital letters. All twelve tests passed.', identity, 'en', 1.0)
        with wave.open(io.BytesIO(audio.audio)) as wav:
            result = {'identity': identity, 'voice': options['voice_bindings'][identity],
                      'elapsed_ms': round((time.perf_counter() - started) * 1000),
                      'content_type': audio.content_type, 'sample_rate': wav.getframerate(),
                      'channels': wav.getnchannels(), 'sample_width': wav.getsampwidth(),
                      'duration_seconds': round(wav.getnframes() / wav.getframerate(), 3),
                      'bytes': len(audio.audio)}
        results.append(result)
    path = Path(__file__).with_name('local-synthesis-results.json')
    path.write_text(json.dumps({'scope': 'Cached model smoke test; first sample includes model initialization; not a quality benchmark.', 'results': results}, indent=2) + '\n')
    print(json.dumps(results))


if __name__ == '__main__':
    asyncio.run(main())
