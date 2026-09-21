import pytest

from noisy_coding import environment


@pytest.mark.parametrize('canonical,legacy,expected', [
    (None, None, '9765'),
    (None, '7765', '7765'),
    ('7765', '9765', '7765'),
    ('', '9765', ''),
])
def test_new_environment_names_win_without_losing_explicit_empty_values(monkeypatch, canonical, legacy, expected):
    for name, value in [('NOISY_STUDIO_LISTENER_PORT', canonical), ('NOISY_CODING_LISTENER_PORT', legacy)]:
        monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv(name, value)

    assert [environment.get(name, '9765') for name in ('NOISY_STUDIO_LISTENER_PORT', 'NOISY_CODING_LISTENER_PORT')] == [expected, expected]


def test_integration_default_does_not_override_legacy_dev_endpoint(monkeypatch):
    monkeypatch.delenv('NOISY_STUDIO_LISTENER_PORT', raising=False)
    monkeypatch.setenv('NOISY_CODING_LISTENER_PORT', '7765')

    assert environment.setdefault('NOISY_STUDIO_LISTENER_PORT', '9765') == '7765'
