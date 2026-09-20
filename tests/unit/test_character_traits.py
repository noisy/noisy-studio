import json

import pytest

from noisy_coding.listener.state import ListenerState
from noisy_coding.listener import daemon, http_api


@pytest.mark.parametrize(("values", "verbosity", "talkative"), [
    ({"brevity": 30, "chatty": 80}, 70, 80),
    ({"brevity": 0, "chatty": 0}, 100, 0),
    ({"brevity": 100, "chatty": 100}, 0, 100),
    ({"verbosity": 70, "talkative": 80}, 70, 80),
    ({"brevity": 90, "verbosity": 70, "chatty": 0, "talkative": 80}, 70, 80),
])
def test_character_input_preserves_behavior_under_canonical_trait_names(values, verbosity, talkative):
    state = ListenerState()

    actual = state.set_character(values)

    assert actual == {
        "humor": 20, "honesty": 60, "verbosity": verbosity,
        "talkative": talkative, "voice": "carina", "speed": 1.0,
    }


def test_default_character_matches_the_existing_visible_slider_values():
    assert ListenerState().character() == {
        "humor": 20, "honesty": 60, "verbosity": 40,
        "talkative": 40, "voice": "carina", "speed": 1.0,
    }


@pytest.mark.parametrize("agent", ["", "session-1"])
def test_saved_characters_are_migrated_once_and_keep_voice_and_behavior(tmp_path, monkeypatch, agent):
    path = tmp_path / "character.json"
    monkeypatch.setattr(daemon, "CHARACTER_FILE", path)
    monkeypatch.setattr(http_api, "CHARACTER_FILE", path)
    old = {"humor": 40, "honesty": 80, "brevity": 30, "chatty": 60,
           "voice": "lux", "speed": 1.2}
    path.write_text(json.dumps({agent: old} if agent else old))
    state = ListenerState()

    daemon.load_saved_characters(state)
    saved = json.loads(path.read_text())
    restarted = ListenerState()
    daemon.load_saved_characters(restarted)

    assert {
        "loaded": state.character(agent), "saved": saved[agent],
        "restarted": restarted.character(agent),
    } == dict.fromkeys(("loaded", "saved", "restarted"), {
        "humor": 40, "honesty": 80, "verbosity": 70, "talkative": 60,
        "voice": "lux", "speed": 1.2,
    })
