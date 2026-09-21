from noisy_studio.listener import daemon
from noisy_studio.listener.state import ListenerState


def test_history_roundtrip_restores_cards_and_id_sequence(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon, "HISTORY_FILE", tmp_path / "history.json")
    state = ListenerState()
    utterance_id = state.create_utterance("user", "recording…")
    state.add_transcript("hello", utterance_id)
    state.create_utterance("claude", "played", text="hi back")
    daemon._save_history(state)

    restored = ListenerState()
    daemon._load_history(restored)

    assert [u["text"] for u in restored.utterances()] == ["hello", "hi back"]
    # New utterances continue the id sequence instead of colliding.
    assert restored.create_utterance("user", "recording…") == 3


def test_load_coerces_in_flight_statuses_to_terminal_ones():
    state = ListenerState()

    state.load_utterances(
        [
            {"id": 1, "role": "user", "status": "transcribing (live)…", "text": ""},
            {"id": 2, "role": "claude", "status": "playing through speakers…", "text": "x"},
            {"id": 3, "role": "user", "status": "delivered to Claude", "text": "done"},
            # The transcript queue died with the old process — an awaiting
            # card would show AWAITING CLAUDE forever.
            {"id": 4, "role": "user", "status": "ready — awaiting pickup", "text": "lost"},
            {"id": 5, "role": "claude", "status": "ready — waiting for the speaker", "text": "y"},
            {"id": 6, "role": "daemon", "status": "queued", "text": "setup words"},
        ]
    )

    statuses = {u["id"]: u["status"] for u in state.utterances()}
    assert statuses[1] == "dropped — daemon restart"
    assert statuses[2] == "unheard — daemon restarted"
    assert statuses[3] == "delivered to Claude"
    assert statuses[4] == "dropped — daemon restart"
    assert statuses[5] == "unheard — daemon restarted"
    assert statuses[6] == "unheard — daemon restarted"  # daemon speech too


def test_load_tolerates_a_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon, "HISTORY_FILE", tmp_path / "absent.json")
    state = ListenerState()

    daemon._load_history(state)

    assert state.utterances() == []
