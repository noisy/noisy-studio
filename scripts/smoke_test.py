"""Live end-to-end check: synthesize a sentence with the real API and play it.

Spends API credits and makes sound. Usage:

    XAI_API_KEY=xai-... uv run python scripts/smoke_test.py "Hello from Grok"
"""

import asyncio
import sys

from noisy_studio import playback, tts


async def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else "Hello! Grok voice is working."
    audio = await tts.synthesize(text, voice_id="eve", language="en", speed=1.0)
    print(f"Synthesized {audio.duration_seconds:.1f}s ({audio.content_type}), playing...")
    await playback.play(audio.audio, audio.content_type)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
