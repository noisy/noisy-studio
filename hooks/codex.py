"""Adapt Codex lifecycle input to the shared hooks; never infer a cwd identity."""

import _environment as environment
import io
import json
import os
import re
import runpy
import sys
import urllib.request
from pathlib import Path

from _codex_config import configure

HOOKS = Path(__file__).resolve().parent
IDENTITY_TOOLS = re.compile(r"^mcp__[^\s]*noisy[_-](coding|studio)[^\s]*__(speak|announce|change_voice)$")
SCRIPTS = {
    "SessionStart": "user_prompt_submit.py",
    "UserPromptSubmit": "user_prompt_submit.py",
    "PreToolUse": "pre_tool_use.py",
    "PostToolUse": "post_tool_use.py",
    "Stop": "stop.py",
}


def warn(message, block=False):
    try:
        port = environment.get("NOISY_CODING_LISTENER_PORT", "8765")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/event",
            data=json.dumps({"kind": "voice_identity_error", "detail": message}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=0.5).close()
    except OSError:
        pass
    output = {"systemMessage": message}
    if block:
        output["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }
    print(json.dumps(output))


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be an object")
        settings = configure()
    except (ValueError, OSError, TypeError) as error:
        warn(f"noisy-coding configuration/input error: {error}", block=True)
        return
    event = payload.get("hook_event_name", "")
    speech_tool = event == "PreToolUse" and bool(IDENTITY_TOOLS.fullmatch(str(payload.get("tool_name", ""))))
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id or not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        warn("noisy-coding: missing or invalid Codex session identity; no voice queue was accessed.", block=speech_tool)
        return
    os.environ["NOISY_CODING_AGENT_NAME"] = session_id
    os.environ["NOISY_CODING_SESSION_TITLE"] = f"{settings.get('agent_label', 'Codex')} · {session_id[:8]}"
    script = SCRIPTS.get(event)
    if script:
        sys.stdin = io.StringIO(json.dumps(payload))
        runpy.run_path(str(HOOKS / script), run_name="__main__")
    if speech_tool:
        arguments = payload.get("tool_input")
        if not isinstance(arguments, dict):
            warn("noisy-coding: speech arguments must be an object.", block=True)
            return
        # Always overwrite model-supplied identity, including a forged value.
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "allow",
            "updatedInput": {**arguments, "agent_id": session_id},
        }}))


if __name__ == "__main__":
    main()
