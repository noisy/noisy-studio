"""Shared, stdlib-only settings for the Grok hooks."""

import json
import os
from pathlib import Path


def config_path():
    return Path(os.environ.get("NOISY_STUDIO_GROK_CONFIG") or
                Path.home() / ".config/noisy-studio/grok.json").expanduser()


def configure():
    path = config_path()
    settings = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(settings, dict):
        raise ValueError("Grok settings must be a JSON object")
    port = int(os.environ.get("NOISY_STUDIO_LISTENER_PORT") or settings.get("port", 9765))
    seconds = float(settings.get("listen_seconds", 600))
    if not 1 <= port <= 65535 or not 0 <= seconds <= 3600:
        raise ValueError("port must be 1–65535 and listen_seconds 0–3600")
    os.environ["NOISY_STUDIO_LISTENER_PORT"] = str(port)
    os.environ["NOISY_STUDIO_REWAKE_WAIT_SECONDS"] = str(seconds)
    os.environ["NOISY_STUDIO_HARNESS"] = "grok"
    os.environ["NOISY_STUDIO_NO_AUTOSPAWN"] = "1"
    return settings
