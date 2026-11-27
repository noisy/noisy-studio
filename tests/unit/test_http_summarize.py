import http.client
import json

import pytest

from noisy_studio.listener.http_api import start_http_api
from noisy_studio.listener.state import ListenerState


@pytest.fixture
def server():
    state = ListenerState()
    server = start_http_api(state, 0)
    yield state, server.server_address[1]
    server.shutdown()


def _post(port: int, path: str, body: dict) -> tuple[int, dict]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("POST", path, body=json.dumps(body))
    response = connection.getresponse()
    answer = (response.status, json.loads(response.read()))
    connection.close()
    return answer


def test_summarize_hands_the_backlog_to_its_agent_and_settles_it_for_good(server):
    state, port = server
    state.register_agent("a1")
    state.register_agent("a2")
    state.set_active_agent("a2")  # the note goes to the clicked tab, not the active one
    state.create_utterance("claude", "unheard — conversation muted", text="Tests are red.", agent="a1")
    state.create_utterance("claude", "queued", text="Fixed - tests are green.", agent="a1")
    state.create_utterance("claude", "unheard — conversation muted", text="Other tab.", agent="a2")

    answer = _post(port, "/summarize-unheard", {"agent": "a1"})

    assert answer == (200, {"summarized": 2})
    assert [(u["agent"], u["status"]) for u in state.utterances()] == [
        ("a1", "skipped — summarized for you"),
        ("a1", "skipped — summarized for you"),
        ("a2", "unheard — conversation muted"),
    ]
    [note] = [message.text for message in state.drain("a1")]
    assert note.startswith("[DASHBOARD] The user pressed Summarize on 2 of your spoken messages")
    assert note.endswith("1. „Tests are red.”\n2. „Fixed - tests are green.”")


def test_summarize_refuses_an_offline_session_and_keeps_its_backlog(server):
    state, port = server
    state.create_utterance("claude", "unheard — conversation muted", text="Still unheard.", agent="gone")

    answer = _post(port, "/summarize-unheard", {"agent": "gone"})

    assert (answer[0], state.utterances()[0]["status"]) == (409, "unheard — conversation muted")
