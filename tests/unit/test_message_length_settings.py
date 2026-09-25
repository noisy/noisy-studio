import http.client
import json

from noisy_studio.listener import http_api
from noisy_studio.listener.state import ListenerState


def test_message_length_defaults_to_ten_minutes_and_http_change_is_persisted(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(http_api, "SETTINGS_FILE", path)
    state = ListenerState()
    assert state.max_utterance_ms == 600_000
    server = http_api.start_http_api(state, 0)
    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
    try:
        connection.request("POST", "/settings", json.dumps({"max_utterance_ms": 900_000}))
        response = connection.getresponse()
        result = json.loads(response.read())
        assert (response.status, result, state.max_utterance_ms, json.loads(path.read_text())["max_utterance_ms"]) == (
            200, {"max_utterance_ms": 900_000}, 900_000, 900_000
        )
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
