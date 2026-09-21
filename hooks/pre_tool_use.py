#!/usr/bin/env python3
"""PreToolUse hook (all tools): report live activity to the dashboard.

Fires when a tool STARTS — the busy bubble shows what Claude is doing at
this very moment. Its counterpart in post_tool_use.py flips the line to
THINKING… once the tool finishes and the model is reasoning again.
Fails open; never blocks the tool call.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _agent_identity import identity  # noqa: E402
from post_tool_use import _activity_line, _post_activity  # noqa: E402

import re  # noqa: E402

IDENTITY_TOOLS = re.compile(
    r"^mcp__[^\s]*noisy[_-]studio[^\s]*__(speak|announce|change_voice|set_speaker_style|acknowledge_delivery)$"
)


def main() -> None:
    raw = sys.stdin.read()
    try:
        hook_input = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return
    agent, _label = identity(hook_input)
    line = _activity_line(hook_input)
    if line:
        _post_activity(agent, line)
    # The MCP server no longer guesses which conversation is speaking: it
    # requires the identity the host hook injects. Installs still on these
    # legacy scripts (the native app's global hooks) must inject it too, or
    # every speak fails with "identity is missing". Overwrites any value the
    # model supplied, forged or stale.
    tool = str(hook_input.get("tool_name") or "")
    if IDENTITY_TOOLS.fullmatch(tool):
        arguments = hook_input.get("tool_input")
        if not isinstance(arguments, dict):
            arguments = {}
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**arguments, "agent_id": agent},
        }}))


if __name__ == "__main__":
    main()
