def test_state_snapshot_digest_ignores_volatile_fields_only():
    from noisy_studio.listener.state_stream import snapshot_digest

    base = {"type": "snapshot", "status": {"agents": ["a"], "nudge_clocks": {"a": 1}, "mic_level": 0.1}, "utterances": []}
    clocks_moved = {**base, "status": {**base["status"], "nudge_clocks": {"a": 2}, "mic_level": 0.7}}
    tab_added = {**base, "status": {**base["status"], "agents": ["a", "b"]}}
    spoke = {**base, "utterances": [{"id": 1}]}
    assert snapshot_digest(base) == snapshot_digest(clocks_moved)
    assert snapshot_digest(base) != snapshot_digest(tab_added)
    assert snapshot_digest(base) != snapshot_digest(spoke)
