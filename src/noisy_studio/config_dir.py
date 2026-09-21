"""Canonical V3 config location; upgrades explicitly copy their existing data.

No automatic move or merge: production and development must stay isolated.
"""
import os
from pathlib import Path

CONFIG_DIR = Path(
    os.environ.get("NOISY_STUDIO_CONFIG_DIR")
    or Path.home() / ".config" / "noisy-studio"
).expanduser()
