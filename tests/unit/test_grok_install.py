import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def installer():
    path = Path(__file__).resolve().parents[2] / "scripts/install_grok.py"
    spec = importlib.util.spec_from_file_location("grok_installer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_install_writes_endpoint_and_hooks_and_uninstall_removes_only_those(installer, tmp_path):
    settings = tmp_path / "grok.json"
    hooks = tmp_path / "noisy-studio.json"
    other = tmp_path / "other.json"
    other.write_text('{"hooks":{"Stop":[{"hooks":[{"command":"my-tool"}]}]}}')
    script = tmp_path / "grok_hook.py"
    script.write_text("#!/usr/bin/env python3\n")
    original = other.read_bytes()

    installer.configure_files(settings, hooks, script, sys.executable, 7765, 60)
    installer.configure_files(settings, hooks, script, sys.executable, 9765, 0)
    saved = json.loads(settings.read_text())
    registered = json.loads(hooks.read_text())

    assert saved == {"managed_by": "noisy-studio", "port": 9765, "listen_seconds": 0}
    assert set(registered["hooks"]) == set(installer.HOOK_EVENTS)
    assert registered["hooks"]["Stop"][0]["hooks"][0]["timeout"] == 30
    assert "grok_hook.py" in registered["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    installer.configure_files(settings, hooks, script, sys.executable, uninstall=True)

    assert not settings.exists()
    assert not hooks.exists()
    assert other.read_bytes() == original


@pytest.mark.parametrize("contents", ['{broken', '{"port": 5555}', '[]'])
def test_installer_refuses_to_replace_unowned_settings(installer, tmp_path, contents):
    settings = tmp_path / "grok.json"
    settings.write_text(contents)
    script = tmp_path / "grok_hook.py"
    script.write_text("#!/usr/bin/env python3\n")

    with pytest.raises(ValueError):
        installer.configure_files(settings, tmp_path / "hooks.json", script, sys.executable, 9765)

    assert settings.read_text() == contents


def test_uninstall_preserves_unknown_settings(installer, tmp_path):
    settings = tmp_path / "grok.json"
    settings.write_text(json.dumps({"managed_by": "noisy-studio", "port": 9765, "other": True}))
    script = tmp_path / "grok_hook.py"
    script.write_text("#!/usr/bin/env python3\n")

    installer.configure_files(settings, tmp_path / "missing.json", script, sys.executable, uninstall=True)

    assert json.loads(settings.read_text()) == {"other": True}
