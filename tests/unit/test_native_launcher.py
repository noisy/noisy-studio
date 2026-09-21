import os
from pathlib import Path
import shlex
import subprocess

import pytest

from noisy_studio import integration, server

LAUNCHER = Path(__file__).resolve().parents[2] / "hooks" / "native.sh"


@pytest.mark.parametrize(("mode", "exit_code"), [("mcp", 0), ("hook", 2)])
def test_native_launcher_preserves_protocol_streams_and_exit_status(tmp_path, mode, exit_code):
    engine = tmp_path / "Engine With Spaces"
    arguments = tmp_path / "arguments"
    received = tmp_path / "input"
    engine.write_text(
        '#!/bin/sh\n'
        f'printf "%s\\n" "$@" > {shlex.quote(str(arguments))}\n'
        f'cat > {shlex.quote(str(received))}\n'
        'printf "protocol response"\n'
        'printf "voice wake" >&2\n'
        f'exit {exit_code}\n'
    )
    engine.chmod(0o700)

    result = subprocess.run(
        ["sh", str(LAUNCHER), mode], input='{"session_id":"session-1"}',
        capture_output=True, text=True, timeout=5,
        env={**os.environ, "NOISY_STUDIO_ENGINE": str(engine)},
    )

    assert {
        "arguments": arguments.read_text().splitlines(), "input": received.read_text(),
        "stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode,
    } == {
        "arguments": ["--integration", mode], "input": '{"session_id":"session-1"}',
        "stdout": "protocol response", "stderr": "voice wake", "exit_code": exit_code,
    }


@pytest.mark.parametrize(("mode", "exit_code", "error"), [
    ("hook", 0, ""),
    ("mcp", 1, "Install the current Noisy Studio app in Applications, then reconnect the voice tools.\n"),
])
def test_missing_app_is_silent_for_hooks_and_actionable_for_tools(tmp_path, mode, exit_code, error):
    result = subprocess.run(
        ["sh", str(LAUNCHER), mode], input="{}", capture_output=True, text=True,
        timeout=5, env={**os.environ, "NOISY_STUDIO_ENGINE": str(tmp_path / "missing")},
    )

    assert (result.returncode, result.stdout, result.stderr) == (exit_code, "", error)


@pytest.mark.parametrize(("configured_port", "expected_port"), [(None, "9765"), ("7765", "7765")])
def test_bundled_mcp_uses_the_selected_endpoint_without_starting_audio(monkeypatch, configured_port, expected_port):
    monkeypatch.delenv("NOISY_STUDIO_LISTENER_PORT", raising=False)
    if configured_port:
        monkeypatch.setenv("NOISY_STUDIO_LISTENER_PORT", configured_port)
    monkeypatch.setenv("NOISY_STUDIO_NO_AUTOSPAWN", "")
    monkeypatch.setenv("NOISY_STUDIO_MCP_TRANSPORT", "http")
    observed = []
    monkeypatch.setattr(server, "main", lambda: observed.append({
        "port": os.environ["NOISY_STUDIO_LISTENER_PORT"],
        "no_autospawn": os.environ["NOISY_STUDIO_NO_AUTOSPAWN"],
        "transport": os.environ["NOISY_STUDIO_MCP_TRANSPORT"],
    }))

    integration.run("mcp")

    assert observed == [{"port": expected_port, "no_autospawn": "1", "transport": "stdio"}]
