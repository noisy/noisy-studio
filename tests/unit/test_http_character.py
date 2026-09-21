import http.client
import json

import pytest

from noisy_studio.listener import http_api
from noisy_studio.listener.http_api import start_http_api
from noisy_studio.listener.state import ListenerState


@pytest.fixture
def character_server(tmp_path, monkeypatch):
    monkeypatch.setattr(http_api, "CHARACTER_FILE", tmp_path / "character.json")
    state = ListenerState()
    server = start_http_api(state, 0)
    yield state, server.server_address[1]
    server.shutdown()


def _post_character(port: int, body: dict) -> None:
    payload = json.dumps(body)
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("POST", "/character", body=payload)
    connection.getresponse().read()
    connection.close()


def test_same_gender_voice_change_never_reaches_the_agent(character_server):
    state, port = character_server

    _post_character(port, {"voice": "luna"})  # default carina (f) → luna (f)

    assert state.drain() == []


@pytest.mark.parametrize(("patch", "expected_values"), [
    pytest.param(
        {"verbosity": 80},
        "humor 20, honesty 60, verbosity 80 (was 40), talkative 40",
        id="one_changed_trait",
    ),
    pytest.param(
        {"verbosity": 80, "talkative": 20, "speed": 1.2},
        "humor 20, honesty 60, verbosity 80 (was 40), talkative 20 (was 40)",
        id="multiple_changes_without_playback_details",
    ),
])
def test_character_instruction_lists_current_values_and_marks_only_changes(character_server, patch, expected_values):
    state, port = character_server

    _post_character(port, patch)

    assert [message.text for message in state.drain()] == [
        f"[CHARACTER] Values /100: {expected_values}. "
        "Apply to replies; acknowledge briefly."
    ]


def test_repeated_character_values_do_not_notify_the_agent_again(character_server):
    state, port = character_server
    state.set_character({"verbosity": 80})

    _post_character(port, {"verbosity": 80})

    assert state.drain() == []


def test_gender_flip_sends_a_silent_persona_instruction(character_server):
    state, port = character_server

    _post_character(port, {"voice": "ara"})  # default carina (f) → ara (f)
    assert state.drain() == []  # same gender — nothing to apply

    _post_character(port, {"voice": "rex"})  # female → male
    transcripts = state.drain()
    assert len(transcripts) == 1
    assert transcripts[0].text.startswith("[PERSONA]")
    assert "male" in transcripts[0].text
    assert "silently" in transcripts[0].text


# --- speaker voice claims via /voice ------------------------------------


def _post_voice(port: int, body: dict) -> tuple[int, dict]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("POST", "/voice", body=json.dumps(body))
    response = connection.getresponse()
    status, payload = response.status, json.loads(response.read())
    connection.close()
    return status, payload


def test_voice_endpoint_moves_a_named_speaker_onto_a_free_voice(
    character_server, tmp_path, monkeypatch
):
    monkeypatch.setattr(http_api, "VOICE_CLAIMS_FILE", tmp_path / "voice-claims.json")
    state, port = character_server

    status, payload = _post_voice(port, {"voice_id": "lux", "speaker": "xfuroo"})

    assert (status, payload["voice"]) == (200, "lux")
    # The claim is what a later /speak reads back for that name.
    assert state.claim_voice("xfuroo", http_api.SUBAGENT_VOICE_POOL, http_api._hash_pick) == "lux"


def test_voice_endpoint_refuses_a_voice_another_speaker_holds(
    character_server, tmp_path, monkeypatch
):
    monkeypatch.setattr(http_api, "VOICE_CLAIMS_FILE", tmp_path / "voice-claims.json")
    state, port = character_server
    _post_voice(port, {"voice_id": "lux", "speaker": "xfuroo"})

    status, payload = _post_voice(port, {"voice_id": "lux", "speaker": "latecomer"})

    assert status == 409
    assert payload["held_by"] == "xfuroo"
    assert "latecomer" not in state.voice_claims()


def test_voice_endpoint_without_a_speaker_still_moves_the_agent(character_server):
    state, port = character_server

    status, payload = _post_voice(port, {"voice_id": "rex"})

    assert (status, payload["voice"]) == (200, "rex")
    assert state.character()["voice"] == "rex"
