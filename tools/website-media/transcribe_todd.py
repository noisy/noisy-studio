"""Replay Todd's actor-only audio through Grok and retain timed partial updates.

Run with the project's Python environment and PYTHONPATH=src. Never transcribes
mixed website audio; agent voices must not enter the actor's captions.
"""
import argparse
import io
import wave
import json
import subprocess
import time
from pathlib import Path

from noisy_studio.listener.stt_stream import StreamingSession
from noisy_studio.listener.stt import transcribe as transcribe_final
from prepare_todd import SCENES, ROOT, digest

SAMPLE_RATE = 24000
CHUNK_SECONDS = 0.1


def transcribe(camera, start, end, offset):
    pcm = subprocess.run([
        'ffmpeg', '-v', 'error', '-ss', str(start / 1000 + offset),
        '-i', str(camera), '-t', str((end - start) / 1000 + 1.0),
        '-vn', '-ac', '1', '-ar', str(SAMPLE_RATE), '-f', 's16le', '-'
    ], check=True, capture_output=True).stdout
    updates = []
    clock = 0.0

    def partial(text):
        if not updates or updates[-1]['text'] != text:
            updates.append({'receivedAtMs': start + (time.monotonic() - clock) * 1000, 'text': text})

    session = StreamingSession(SAMPLE_RATE, 'en', partial)
    clock = time.monotonic()
    chunk_bytes = int(SAMPLE_RATE * 2 * CHUNK_SECONDS)
    try:
        for position in range(0, len(pcm), chunk_bytes):
            # Feed at recording speed, not as a batch. Arrival timestamps then
            # describe genuine streaming updates on the media clock.
            due = clock + position / (SAMPLE_RATE * 2)
            time.sleep(max(0, due - time.monotonic()))
            session.send(pcm[position:position + chunk_bytes])
        time.sleep(max(0, clock + len(pcm) / (SAMPLE_RATE * 2) - time.monotonic()))
        # Let streaming recognition finalize the last words. The silence is
        # decoder input only, never added to the video or scenario timeline.
        for _ in range(10):
            session.send(bytes(chunk_bytes))
            time.sleep(CHUNK_SECONDS)
        final = session.finish()
    finally:
        session.abort()
    if not final or not updates:
        raise RuntimeError('No streaming transcript received')
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)
    polished = transcribe_final(wav_buffer.getvalue(), 'en')
    if not polished:
        raise RuntimeError('Empty final transcript')
    return {'updates': updates, 'streamingFinal': final, 'final': polished, 'finalAtMs': max(end, updates[-1]['receivedAtMs'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('delivery', type=Path)
    args = parser.parse_args()
    output = ROOT / 'website/src/assets/todd'
    for scene, prefix, title, offset in SCENES:
        camera = args.delivery / f'Todd - {title}.mp4'
        journal, = args.delivery.glob(prefix + '*.json')
        take = json.loads(journal.read_text())
        result = {'provider': 'xAI Grok streaming STT', 'sourceSha256': digest(camera), 'cameraOffsetSeconds': offset, 'utterances': {}}
        for start in (e for e in take['events'] if e['type'] == 'user-start'):
            identity = start['utterance']
            end = next(e for e in take['events'] if e['type'] == 'user-end' and e['utterance'] == identity)
            result['utterances'][identity] = transcribe(camera, start['atMs'], end['atMs'], offset)
            print(scene, identity, result['utterances'][identity]['final'], flush=True)
        (output / f'{scene}-transcripts.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Provider errors can contain credential-bearing headers; never log them.
        raise SystemExit(f'Transcription failed ({type(error).__name__}); no credential details logged.') from None
