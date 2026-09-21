#!/usr/bin/env python3
"""The one Claude Code hook script: every lifecycle event goes through here.

Registered for SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
Stop, SubagentStart and SubagentStop (see hooks/hooks.json). The daemon's
claude-hooks adapter decides what each payload means; this script only
carries it there and acts on the answer. Fails open without a daemon.
"""

from __future__ import annotations

import _environment as environment
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_flow  # noqa: E402


def main() -> None:
    payload = _hook_flow.read_payload()
    if not payload:
        return
    if payload.get("hook_event_name") in ("SessionStart", "UserPromptSubmit") and not payload.get("agent_id"):
        # Read only the inherited endpoint. Never print it or derive it from an ID.
        payload["noisy_studio_connection"] = {"socket": environment.get("CLAUDE_CODE_MESSAGING_SOCKET", ""), "hook_protocol": 2}
    # Optional: shorten the listening window (seconds); the daemon never
    # lets a hook lengthen it past the harness default.
    window = environment.get("NOISY_CODING_REWAKE_WAIT_SECONDS")
    try:
        code = _hook_flow.run(
            "claude-hooks", payload, listen_seconds=float(window) if window else None
        )
    except Exception:
        return
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
