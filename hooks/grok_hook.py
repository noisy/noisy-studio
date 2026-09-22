#!/usr/bin/env python3
"""The one Grok hook script: every lifecycle event goes through here.

Same flow as the Codex hook. The endpoint comes from
~/.config/noisy-studio/grok.json, and the Stop hook is synchronous, so the
turn stays open while it listens. Grok's stdin is camelCase; the fields the
shared flow already understands are filled in before the payload is sent.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _grok_config import configure  # noqa: E402

_EVENTS = {
    "session_start": "SessionStart",
    "session_end": "SessionEnd",
    "user_prompt_submit": "UserPromptSubmit",
    "pre_tool_use": "PreToolUse",
    "post_tool_use": "PostToolUse",
    "stop": "Stop",
    "subagent_start": "SubagentStart",
    "subagent_stop": "SubagentStop",
}


def normalize(payload: dict) -> dict:
    """Copy Grok's camelCase fields onto the names the shared hook flow reads."""
    normalized = dict(payload)
    if not normalized.get("session_id") and normalized.get("sessionId"):
        normalized["session_id"] = normalized["sessionId"]
    if not normalized.get("tool_name") and normalized.get("toolName"):
        normalized["tool_name"] = normalized["toolName"]
    if not isinstance(normalized.get("tool_input"), dict) and isinstance(normalized.get("toolInput"), dict):
        normalized["tool_input"] = normalized["toolInput"]
    if not normalized.get("hook_event_name"):
        normalized["hook_event_name"] = _EVENTS.get(str(normalized.get("hookEventName") or ""), "")
    return normalized


def main() -> None:
    try:
        configure()
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"systemMessage": f"noisy-studio configuration error: {error}"}))
        return
    import _hook_flow  # after configure(): the port is in the environment

    raw = _hook_flow.read_payload()
    if not raw:
        return
    payload = normalize(raw)
    window = os.environ.get("NOISY_STUDIO_REWAKE_WAIT_SECONDS")
    try:
        code = _hook_flow.run("grok-hooks", payload, listen_seconds=float(window) if window else None)
    except Exception:
        return
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
