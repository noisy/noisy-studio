import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def installer():
    path = Path(__file__).resolve().parents[2] / "scripts/install_codex.py"
    spec = importlib.util.spec_from_file_location("codex_installer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repeated_install_and_uninstall_preserve_unrelated_configuration(installer, tmp_path):
    hooks = tmp_path / "hooks.json"
    hooks.write_text('{"hooks":{"Stop":[{"hooks":[{"command":"my-tool"}]}]}}')
    config = tmp_path / "config.toml"
    config.write_text('[mcp_servers.other]\ncommand = "other"\n')
    originals = {path.name: path.read_bytes() for path in (hooks, config)}
    settings = tmp_path / "integration.json"

    installer.configure_file(settings, 9765, 60)
    installer.configure_file(settings, 12345, 0)
    assert json.loads(settings.read_text()) == {
        "managed_by": "noisy-studio", "port": 12345, "listen_seconds": 0, "agent_label": "Codex",
    }
    installer.configure_file(settings, uninstall=True)

    assert not settings.exists()
    assert {path.name: path.read_bytes() for path in (hooks, config)} == originals


@pytest.mark.parametrize("contents", ['{broken', '{"port": 5555}', '[]'])
def test_installer_refuses_to_replace_invalid_or_unowned_settings(installer, tmp_path, contents):
    path = tmp_path / "codex.json"
    path.write_text(contents)

    with pytest.raises(ValueError):
        installer.configure_file(path, 9765)

    assert path.read_text() == contents


def test_uninstall_preserves_unknown_settings(installer, tmp_path):
    path = tmp_path / "codex.json"
    path.write_text(json.dumps({"managed_by": "noisy-studio", "port": 9765, "other": True}))

    installer.configure_file(path, uninstall=True)

    assert json.loads(path.read_text()) == {"other": True}
