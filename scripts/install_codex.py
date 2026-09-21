#!/usr/bin/env python3
"""Configure the Codex integration without editing Codex-owned settings."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from _codex_config import config_path  # noqa: E402

OWNER = "noisy-studio"
MANAGED_KEYS = {"managed_by", "port", "listen_seconds", "agent_label"}


def configure_file(path, port=None, listen_seconds=3600, agent_label="Codex", uninstall=False):
    existing = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(existing, dict):
        raise ValueError("existing integration settings must be a JSON object")
    if existing and existing.get("managed_by") != OWNER:
        raise ValueError("existing file is not owned by this installer; preserve or move it explicitly first")
    if uninstall:
        result = {key: value for key, value in existing.items() if key not in MANAGED_KEYS}
        if not result:
            path.unlink(missing_ok=True)
            return
    else:
        if port is None or not 1 <= port <= 65535 or not 0 <= listen_seconds <= 3600:
            raise ValueError("port must be 1–65535 and listen-seconds 0–3600")
        result = {**existing, "managed_by": OWNER, "port": port,
                  "listen_seconds": listen_seconds, "agent_label": agent_label}
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".codex-")
    try:
        with os.fdopen(descriptor, "w") as output:
            json.dump(result, output, indent=2)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, help="daemon port: app 9765, dev 7765, or your custom port")
    parser.add_argument("--listen-seconds", type=int, default=3600, help="idle listening window, 0 disables Stop listening")
    parser.add_argument("--agent-label", default="Codex", help="display name prefix; session IDs remain unique")
    parser.add_argument("--uninstall", action="store_true", help="remove only settings owned by this installer")
    args = parser.parse_args()
    try:
        configure_file(config_path(), args.port, args.listen_seconds, args.agent_label, args.uninstall)
    except (OSError, ValueError) as error:
        parser.exit(1, f"No settings changed: {error}\n")
    print("Integration settings removed." if args.uninstall else
          f"Endpoint configured on port {args.port}. Review /hooks and start a new Codex session; verify a spoken round trip.")


if __name__ == "__main__":
    main()
