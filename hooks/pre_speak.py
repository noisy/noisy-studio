#!/usr/bin/env python3
"""PreToolUse hook on noisy-studio speak: show the user what is about to be said.

Prints a systemMessage so the terminal shows the spoken text next to the
tool-call spinner. Never blocks the call.
"""

import json
import sys

MAX_PREVIEW_CHARS = 220


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
        tool_input = payload.get("tool_input", {})
        text = str(tool_input.get("text", "")).strip()
        voice = str(tool_input.get("voice_id", "")) or "carina"
    except Exception:
        return
    if not text:
        return
    if len(text) > MAX_PREVIEW_CHARS:
        text = text[: MAX_PREVIEW_CHARS - 1] + "…"
    print(json.dumps({"systemMessage": f"🔊 {voice}: „{text}”"}))


if __name__ == "__main__":
    main()
