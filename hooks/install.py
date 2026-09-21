#!/usr/bin/env python3
"""One-shot hook installer for a local checkout.

    python3 hooks/install.py            # daemon on the default port (8765)
    python3 hooks/install.py --port 7765

Registers the noisy-studio hooks in ~/.claude/settings.json (user scope):
one script, hooks/claude_hook.py, for every lifecycle event, run with the
plain `python3` from PATH (stdlib only, python 3.9+). Idempotent: existing
noisy-studio entries are replaced in place, everything else in the file is
preserved. Restart Claude Code afterwards - hooks are read at startup.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
SETTINGS = Path.home() / ".claude" / "settings.json"
SCRIPT = HOOKS_DIR / "claude_hook.py"
# The listener waits this long for voice before the tab goes deaf. The hook
# timeout must outlive it (slack for the wake itself).
LISTEN_SECONDS = 14400  # 4h idle window (U1: no hook-timeout cap); deaf state is the fallback
LISTENER_EVENTS = ("SessionStart", "Stop")
QUICK_EVENTS = ("UserPromptSubmit", "SubagentStart", "SubagentStop", "SessionEnd")
TOOL_EVENTS = ("PreToolUse", "PostToolUse")


def _command(port: int | None) -> str:
    prefix = f"NOISY_STUDIO_LISTENER_PORT={port} " if port else ""
    return f'{prefix}python3 "{SCRIPT}"'


def _hook(command: str, timeout: int, status: str, **extra) -> dict:
    return {"type": "command", "command": command, "timeout": timeout, "statusMessage": status, **extra}


def entries(port: int | None = None) -> dict:
    command = _command(port)
    listener = _hook(
        command, LISTEN_SECONDS + 30, "Listening for your voice",
        asyncRewake=True, rewakeSummary="🎙️ Voice message received",
    )
    hooks: dict = {}
    for event in LISTENER_EVENTS:
        hooks[event] = [{"hooks": [dict(listener)]}]
    for event in QUICK_EVENTS:
        hooks[event] = [{"hooks": [_hook(command, 5, "Reporting activity")]}]
    for event in TOOL_EVENTS:
        hooks[event] = [{"matcher": "*", "hooks": [_hook(command, 5, "Reporting activity")]}]
    return hooks


def _is_ours(entry: dict) -> bool:
    return any(
        "noisy-studio" in hook.get("command", "") or str(HOOKS_DIR) in hook.get("command", "")
        for hook in entry.get("hooks", [])
    )


def install(settings_path: Path, port: int | None = None) -> None:
    settings: dict = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text() or "{}")
    hooks = settings.setdefault("hooks", {})
    for event, ours in entries(port).items():
        kept = [e for e in hooks.get(event, []) if not _is_ours(e)]
        hooks[event] = kept + ours
    # Events we used to register but no longer do keep only foreign entries.
    for event in list(hooks):
        if event not in entries(port):
            hooks[event] = [e for e in hooks[event] if not _is_ours(e)]
            if not hooks[event]:
                del hooks[event]
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=None, help="daemon HTTP port (default 8765)")
    args = parser.parse_args()
    install(SETTINGS, args.port)
    print(f"noisy-studio hooks registered in {SETTINGS}")
    print("Restart Claude Code to activate them.")


if __name__ == "__main__":
    main()
