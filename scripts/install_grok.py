#!/usr/bin/env python3
"""Register the Grok voice hooks without editing unrelated Grok settings."""

import argparse
import json
import os
import shlex
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from _grok_config import config_path  # noqa: E402

OWNER = "noisy-studio"
MANAGED_KEYS = {"managed_by", "port", "listen_seconds"}
HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "SubagentStart",
    "SubagentStop",
    "SessionEnd",
    "Stop",
)


def hooks_path():
    return Path(os.environ.get("NOISY_STUDIO_GROK_HOOKS") or
                Path.home() / ".grok" / "hooks" / "noisy-studio.json").expanduser()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".grok-")
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def hook_document(python: str, script: str, listen_seconds: int) -> dict:
    command = " ".join(shlex.quote(part) for part in (python, script))
    stop_timeout = listen_seconds + 30
    hooks = {}
    for event in HOOK_EVENTS:
        hooks[event] = [{
            "hooks": [{
                "type": "command",
                "command": command,
                "timeout": stop_timeout if event == "Stop" else 10,
            }],
        }]
    return {"hooks": hooks}


def _owned_hook_file(path: Path, script: str) -> bool:
    if not path.exists():
        return True
    try:
        document = json.loads(path.read_text())
    except ValueError:
        return False
    if not isinstance(document, dict):
        return False
    groups = document.get("hooks")
    if not isinstance(groups, dict):
        return False
    for event in HOOK_EVENTS:
        entries = groups.get(event)
        if not isinstance(entries, list):
            return False
        commands = [
            hook.get("command", "")
            for group in entries if isinstance(group, dict)
            for hook in group.get("hooks", []) if isinstance(hook, dict)
        ]
        if not commands or any(script not in command for command in commands):
            return False
    return set(groups) <= set(HOOK_EVENTS)


def configure_files(settings: Path, hooks: Path, script: Path, python: str,
                    port=None, listen_seconds=600, uninstall=False):
    existing = json.loads(settings.read_text()) if settings.exists() else {}
    if not isinstance(existing, dict):
        raise ValueError("existing integration settings must be a JSON object")
    if existing and existing.get("managed_by") != OWNER:
        raise ValueError("existing file is not owned by this installer; preserve or move it explicitly first")
    if not _owned_hook_file(hooks, str(script)):
        raise ValueError("hook file is not owned by this installer; preserve or move it explicitly first")
    if uninstall:
        result = {key: value for key, value in existing.items() if key not in MANAGED_KEYS}
        if result:
            _write(settings, json.dumps(result, indent=2) + "\n")
        else:
            settings.unlink(missing_ok=True)
        hooks.unlink(missing_ok=True)
        return
    if port is None or not 1 <= port <= 65535 or not 0 <= listen_seconds <= 3600:
        raise ValueError("port must be 1–65535 and listen-seconds 0–3600")
    if not script.is_file():
        raise ValueError("hook script does not exist")
    _write(settings, json.dumps(
        {**existing, "managed_by": OWNER, "port": port, "listen_seconds": listen_seconds},
        indent=2,
    ) + "\n")
    document = hook_document(python, str(script), listen_seconds)
    _write(hooks, json.dumps(document, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, help="daemon port: app 9765, dev 7765, or your custom port")
    parser.add_argument("--listen-seconds", type=int, default=600,
                        help="idle listening window, 0 disables Stop listening, max 3600")
    parser.add_argument("--python", default=sys.executable, help="Python 3.10+ used to run the hook")
    parser.add_argument("--uninstall", action="store_true", help="remove only settings owned by this installer")
    args = parser.parse_args()
    script = Path(__file__).resolve().parents[1] / "hooks" / "grok_hook.py"
    try:
        configure_files(
            config_path(), hooks_path(), script, args.python,
            args.port, args.listen_seconds, args.uninstall,
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"No settings changed: {error}\n")
    print("Integration settings removed." if args.uninstall else
          "Grok hooks registered. Start a new Grok session, then verify a spoken round trip.")


if __name__ == "__main__":
    main()
