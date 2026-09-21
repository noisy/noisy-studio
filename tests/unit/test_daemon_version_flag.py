"""#100: the frozen daemon must be able to say which version it is."""

from __future__ import annotations

from noisy_studio.listener import daemon
from noisy_studio.listener.http_api import DAEMON_VERSION


def test_version_flag_prints_the_version_and_never_opens_audio(monkeypatch, capsys):
    monkeypatch.setattr(daemon.sys, "argv", ["noisy-studio-daemon", "--version"])
    monkeypatch.setattr(daemon, "run", lambda: (_ for _ in ()).throw(AssertionError("run() must not start")))
    daemon.main()
    assert capsys.readouterr().out.strip() == DAEMON_VERSION
    assert DAEMON_VERSION != "dev"  # the dev venv has metadata; the frozen build must too


def test_display_version_speaks_the_tag_dialect():
    from noisy_studio.listener.http_api import display_version

    assert display_version("3.0.0a4") == "3.0.0-alpha.4"
    assert display_version("3.1.0b2") == "3.1.0-beta.2"
    assert display_version("3.1.0rc1") == "3.1.0-rc.1"
    assert display_version("2.17.0") == "2.17.0"
    assert display_version("dev") == "dev"
