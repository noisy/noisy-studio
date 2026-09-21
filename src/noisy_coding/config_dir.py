"""Single source of truth for the on-disk config directory.

Every persistent file (API key, settings, character, history, session map,
rewake locks) lives under CONFIG_DIR. Defining it once keeps the readers in
sync and gives the rename a single place to migrate the old location from.
"""

from noisy_coding import environment
import os
from pathlib import Path

# Overridable so a second instance can be genuinely SEPARATE, not merely on
# another port. Two daemons sharing this directory share the API key (handy)
# but also the settings, the history and the voice-claim ledger - and the
# last writer wins. A sandbox for testing the desktop app wants its own.
CONFIG_DIR = Path(
    environment.get("NOISY_CODING_CONFIG_DIR")
    or Path.home() / ".config" / "noisy-coding"
).expanduser()
_LEGACY_CONFIG_DIR = Path.home() / ".config" / "grok-voice"


def migrate_legacy_config_dir() -> None:
    """Carry the user's data across the grok-voice -> noisy-coding rename.

    The old directory holds the xAI API key, character, settings and
    conversation history — losing them would force a re-setup — so on the
    first daemon startup under the new name we move each legacy file into
    the new directory.

    We move file-by-file (not a single dir rename) and skip any name that
    already exists at the destination: the hooks write sessions.json to the
    new path the moment a session starts, so the new directory can already
    exist before the daemon ever runs. A blanket "new dir must not exist"
    guard would then wrongly skip the whole migration and hide the API key.
    """
    if not _LEGACY_CONFIG_DIR.is_dir():
        return
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for legacy_file in _LEGACY_CONFIG_DIR.iterdir():
        destination = CONFIG_DIR / legacy_file.name
        if not destination.exists():
            legacy_file.rename(destination)
