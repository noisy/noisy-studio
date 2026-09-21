import http.client
import json

from noisy_coding.listener.http_api import start_http_api
from noisy_coding.listener.state import ListenerState


def test_set_mic_level_clamps_to_unit_range():
    state = ListenerState()

    state.set_mic_level(0.42)
    assert state.mic_level == 0.42

    state.set_mic_level(7.0)
    assert state.mic_level == 1.0

    state.set_mic_level(-1.0)
    assert state.mic_level == 0.0


def test_ptt_hold_barges_in_on_playback_only_in_ptt_mode(monkeypatch):
    import json as json_module

    from noisy_coding.listener import http_api as http_api_module

    stops = []
    monkeypatch.setattr(http_api_module.playback, "stop_all_players", lambda: stops.append(1))
    state = ListenerState()
    server = start_http_api(state, 0)
    port = server.server_address[1]

    def post_ptt_held():
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("POST", "/ptt", body=json_module.dumps({"held": True}),
                           headers={"Content-Length": "14"})
        connection.getresponse().read()
        connection.close()

    try:
        state.set_detection_mode("auto")
        post_ptt_held()
        assert stops == []  # auto: noise must not cancel Claude's speech

        state.set_detection_mode("ptt")
        post_ptt_held()
        assert stops == [1]  # ptt: the held button outranks playback
    finally:
        server.shutdown()


def test_speak_with_interrupt_stops_native_playback(monkeypatch):
    from concurrent.futures import Future

    from noisy_coding.listener import http_api as http_api_module

    stops = []


    monkeypatch.setattr(
        http_api_module.playback, "stop_all_players", lambda: stops.append("local")
    )
    monkeypatch.setattr(http_api_module.speech, "submit", lambda *_a, **_k: Future())

    state = ListenerState()
    server = start_http_api(state, 0)
    port = server.server_address[1]
    try:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        body = json.dumps({"text": "next clip", "interrupt": True, "wait": False})
        connection.request(
            "POST", "/speak", body=body, headers={"Content-Length": str(len(body))}
        )
        connection.getresponse().read()
        connection.close()
    finally:
        server.shutdown()

    assert stops == ["local"]


def test_diagnose_requires_an_api_key(monkeypatch):
    from noisy_coding.listener import http_api as http_api_module

    monkeypatch.setattr(http_api_module.credentials, "api_key", lambda: "")
    state = ListenerState()
    server = start_http_api(state, 0)
    port = server.server_address[1]
    try:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/diagnose")
        response = connection.getresponse()
        assert response.status == 400
        response.read()
        connection.close()
    finally:
        server.shutdown()


def test_diagnose_returns_the_per_check_breakdown(monkeypatch):
    from noisy_coding.listener import http_api as http_api_module

    checks = {
        "api_key": {"ok": True, "ms": 120},
        "tts_stream": {"ok": False, "detail": "HTTP 400 Incorrect API key"},
    }
    monkeypatch.setattr(http_api_module.credentials, "api_key", lambda: "xai-secret")
    monkeypatch.setattr(
        http_api_module.diagnostics, "run_checks_sync", lambda *_a, **_k: checks
    )
    state = ListenerState()
    server = start_http_api(state, 0)
    port = server.server_address[1]
    try:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/diagnose")
        response = connection.getresponse()
        assert response.status == 200
        body = json.loads(response.read())
        connection.close()
    finally:
        server.shutdown()

    assert body == {"checks": checks}


def _post_credentials(port: int, key: str) -> tuple[int, dict]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps({"xai_api_key": key})
    connection.request(
        "POST", "/credentials", body=body,
        headers={"Content-Length": str(len(body))},
    )
    response = connection.getresponse()
    payload = json.loads(response.read())
    connection.close()
    return response.status, payload


def _fake_key_store(monkeypatch, initial: str = ""):
    from noisy_coding.listener import http_api as http_api_module

    store = {"key": initial}
    monkeypatch.setattr(
        http_api_module.credentials, "save_api_key",
        lambda key: store.__setitem__("key", key),
    )
    monkeypatch.setattr(
        http_api_module.credentials, "delete_api_key",
        lambda: store.__setitem__("key", ""),
    )
    monkeypatch.setattr(http_api_module.credentials, "api_key", lambda: store["key"])
    monkeypatch.setattr(http_api_module.credentials, "api_key_hint", lambda: "····abcd")
    return store


def test_saving_a_verified_key_reports_the_checks_and_speaks(monkeypatch):
    from noisy_coding.listener import http_api as http_api_module

    checks = {"api_key": {"ok": True, "ms": 90}}
    store = _fake_key_store(monkeypatch)
    spoken = []
    monkeypatch.setattr(
        http_api_module.diagnostics, "run_checks_sync", lambda *_a, **_k: checks
    )
    monkeypatch.setattr(
        http_api_module.speech, "submit",
        lambda _state, text, **_k: spoken.append(text),
    )
    state = ListenerState()
    server = start_http_api(state, 0)
    try:
        status, payload = _post_credentials(server.server_address[1], "xai-new-key")
    finally:
        server.shutdown()

    assert status == 200
    assert store["key"] == "xai-new-key"
    assert payload["api_key_set"] is True
    assert payload["checks"] == checks
    assert spoken and "accepted" in spoken[0]  # audible proof the voice path works
    assert "Select your microphone" in spoken[0]  # default mic → no activation step needed




def test_a_key_failing_verification_is_never_accepted(monkeypatch):
    from noisy_coding.listener import http_api as http_api_module

    checks = {"api_key": {"ok": False, "detail": "HTTP 401: invalid key"}}
    store = _fake_key_store(monkeypatch, initial="xai-old-working")
    monkeypatch.setattr(
        http_api_module.diagnostics, "run_checks_sync", lambda *_a, **_k: checks
    )
    state = ListenerState()
    server = start_http_api(state, 0)
    try:
        status, payload = _post_credentials(server.server_address[1], "xai-dead-key")
    finally:
        server.shutdown()

    assert status == 400
    assert store["key"] == "xai-old-working"  # rollback, the old key survives
    assert payload["api_key_set"] is True  # the OLD key still counts
    assert payload["checks"] == checks


def test_a_rejected_first_key_leaves_the_daemon_unconfigured(monkeypatch):
    from noisy_coding.listener import http_api as http_api_module

    checks = {"api_key": {"ok": False, "detail": "HTTP 401: invalid key"}}
    store = _fake_key_store(monkeypatch, initial="")
    monkeypatch.setattr(
        http_api_module.diagnostics, "run_checks_sync", lambda *_a, **_k: checks
    )
    state = ListenerState()
    server = start_http_api(state, 0)
    try:
        status, payload = _post_credentials(server.server_address[1], "xai-dead-key")
    finally:
        server.shutdown()

    assert status == 400
    assert store["key"] == ""  # first contact stays unconfigured
    assert payload["api_key_set"] is False


def test_stream_mic_serves_sse_frames_with_level_and_recording():
    state = ListenerState()
    state.set_mic_level(0.5)
    state.set_recording(True)
    server = start_http_api(state, 0)
    port = server.server_address[1]

    try:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/stream/mic")
        response = connection.getresponse()

        assert response.status == 200
        assert response.getheader("Content-Type") == "text/event-stream"
        line = response.fp.readline().decode()
        assert line.startswith("data: ")
        frame = json.loads(line[len("data: "):])
        assert frame == {"level": 0.5, "recording": True}

        connection.close()
    finally:
        server.shutdown()
