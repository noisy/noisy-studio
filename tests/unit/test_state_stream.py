def test_state_snapshot_digest_ignores_volatile_fields_only():
    from noisy_studio.listener.state_stream import snapshot_digest

    base = {"type": "snapshot", "status": {"agents": ["a"], "nudge_clocks": {"a": 1}, "mic_level": 0.1}, "utterances": []}
    clocks_moved = {**base, "status": {**base["status"], "nudge_clocks": {"a": 2}, "mic_level": 0.7}}
    tab_added = {**base, "status": {**base["status"], "agents": ["a", "b"]}}
    spoke = {**base, "utterances": [{"id": 1}]}
    assert snapshot_digest(base) == snapshot_digest(clocks_moved)
    assert snapshot_digest(base) != snapshot_digest(tab_added)
    assert snapshot_digest(base) != snapshot_digest(spoke)


def test_character_change_updates_status_and_stream_digest():
    from noisy_studio.listener.http_api import state_snapshot, status_payload
    from noisy_studio.listener.state import ListenerState
    from noisy_studio.listener.state_stream import snapshot_digest

    state = ListenerState()
    state.register_agent("a1")
    before = state_snapshot(state)
    saved = state.set_character({"voice": "iris", "humor": 80}, "a1")
    after = state_snapshot(state)

    assert after["status"]["agent_characters"]["a1"] == saved
    assert status_payload(state)["agent_characters"]["a1"] == saved
    assert snapshot_digest(before) != snapshot_digest(after)


def test_provider_capability_change_reaches_status_and_stream(monkeypatch):
    from noisy_studio.listener import http_api
    from noisy_studio.listener.state import ListenerState
    from noisy_studio.listener.state_stream import snapshot_digest

    capabilities = {'version': 1, 'stt': {'model': 'model-a'}, 'tts': None}
    monkeypatch.setattr(http_api, 'audio_capabilities', lambda: dict(capabilities))
    state = ListenerState()
    before = http_api.state_snapshot(state)
    capabilities['stt'] = {'model': 'model-b'}
    after = http_api.state_snapshot(state)

    assert (http_api.status_payload(state)['audio_capabilities'],
            after['status']['audio_capabilities'],
            snapshot_digest(before) != snapshot_digest(after)) == (capabilities, capabilities, True)
