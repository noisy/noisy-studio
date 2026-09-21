#!/usr/bin/env python3
"""The one Codex hook script: every lifecycle event goes through here.

Same flow as claude_hook.py with two Codex facts: the endpoint comes from
~/.config/noisy-studio/codex.json (both hooks and MCP read it, so they
always agree), and the Stop hook is synchronous, so its listening window is
the short one the user configured - the turn stays open while we listen.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _codex_config import configure  # noqa: E402


def main() -> None:
    try:
        settings = configure()
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"systemMessage": f"noisy-studio configuration error: {error}"}))
        return
    import _hook_flow  # after configure(): the port comes from the settings file

    payload = _hook_flow.read_payload()
    if not payload:
        return
    listen_seconds = float(os.environ.get("NOISY_STUDIO_REWAKE_WAIT_SECONDS", "30"))
    try:
        code = _hook_flow.run("codex-hooks", payload, listen_seconds=listen_seconds)
    except Exception:
        return
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
