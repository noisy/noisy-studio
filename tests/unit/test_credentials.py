import stat

from noisy_studio import credentials


def test_api_key_roundtrip_with_private_file(tmp_path, monkeypatch):
    monkeypatch.setattr(credentials, "CREDENTIALS_FILE", tmp_path / "credentials.json")

    assert credentials.api_key() == ""
    credentials.save_api_key("  xai-secret-key-1234  ")

    assert credentials.api_key() == "xai-secret-key-1234"
    mode = stat.S_IMODE((tmp_path / "credentials.json").stat().st_mode)
    assert mode == 0o600


def test_api_key_hint_shows_only_the_tail(tmp_path, monkeypatch):
    monkeypatch.setattr(credentials, "CREDENTIALS_FILE", tmp_path / "credentials.json")
    credentials.save_api_key("xai-secret-key-1234")

    hint = credentials.api_key_hint()

    assert hint == "····1234"
    assert "secret" not in hint


def test_unreadable_or_missing_file_means_no_key(tmp_path, monkeypatch):
    monkeypatch.setattr(credentials, "CREDENTIALS_FILE", tmp_path / "nope.json")
    assert credentials.api_key() == ""

    (tmp_path / "broken.json").write_text("not json")
    monkeypatch.setattr(credentials, "CREDENTIALS_FILE", tmp_path / "broken.json")
    assert credentials.api_key() == ""
