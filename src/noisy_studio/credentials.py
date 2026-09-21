"""The xAI API key lives in one file, configured from the dashboard.

Deliberately no env-var fallback: one source of truth keeps setup simple
("paste the key into the dashboard"), and every reader picks up a new key
on the next API call — no restarts.
"""

import json

from noisy_studio.config_dir import CONFIG_DIR

CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def api_key() -> str:
    """The stored xAI API key, or "" when not configured yet."""
    try:
        return str(json.loads(CREDENTIALS_FILE.read_text()).get("xai_api_key", ""))
    except (OSError, ValueError):
        return ""


def save_api_key(key: str) -> None:
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps({"xai_api_key": key.strip()}))
    CREDENTIALS_FILE.chmod(0o600)


def delete_api_key() -> None:
    """Back to unconfigured — used when a candidate key fails verification
    and there is no previous key to fall back to."""
    CREDENTIALS_FILE.unlink(missing_ok=True)


def api_key_hint() -> str:
    """Safe display form: last 4 characters only (never the full key)."""
    key = api_key()
    return f"····{key[-4:]}" if len(key) >= 8 else ""
