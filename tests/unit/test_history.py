from noisy_studio.listener import daemon
from noisy_studio.listener.state import ListenerState


def test_history_roundtrip_restores_cards_and_id_sequence(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon, "HISTORY_FILE", tmp_path / "history.json")
    monkeypatch.setattr(daemon, "PENDING_FILE", tmp_path / "pending.json")
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
    monkeypatch.setattr(daemon, "PENDING_FILE", tmp_path / "pending.json")
    state = ListenerState()

    daemon._load_history(state)

    assert state.utterances() == []


def test_busy_conversation_and_system_events_do_not_evict_idle_histories():
    state = ListenerState()
    first = state.create_utterance('claude', 'played', text='first reply', agent='a1')
    second = state.create_utterance('user', 'delivered', text='second question', agent='a2')
    for index in range(250):
        state.create_utterance('claude', 'played', text=str(index), agent='a3')
        state.create_utterance('system', '', text='Microphone changed', agent='a1')

    assert {
        'a1': [row['id'] for row in state.utterances('a1') if row['role'] != 'system'],
        'a2': [row['id'] for row in state.utterances('a2')],
        'a3_count': len(state.utterances('a3')),
        'system_count': sum(row['role'] == 'system' for row in state.utterances()),
        'trimmed': state.history_trimmed(),
    } == {'a1': [first], 'a2': [second], 'a3_count': 200, 'system_count': 100, 'trimmed': {'a3': 50}}


def test_per_conversation_history_and_trim_notice_survive_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon, 'HISTORY_FILE', tmp_path / 'history.json')
    monkeypatch.setattr(daemon, 'PENDING_FILE', tmp_path / 'pending.json')
    state = ListenerState()
    state.create_utterance('claude', 'played', text='quiet reply', agent='a1')
    for index in range(205):
        state.create_utterance('claude', 'played', text=str(index), agent='a2')
    saved = state.snapshot_utterances()
    daemon._save_history(state)

    restored = ListenerState()
    daemon._load_history(restored)

    assert restored.snapshot_utterances() == saved
    assert restored.history_trimmed() == {'a2': 5}
    assert restored.create_utterance('user', 'recording', agent='a1') == 207


def test_legacy_history_migrates_without_losing_surviving_cards(tmp_path, monkeypatch):
    import json

    history_file = tmp_path / 'history.json'
    monkeypatch.setattr(daemon, 'HISTORY_FILE', history_file)
    monkeypatch.setattr(daemon, 'PENDING_FILE', tmp_path / 'pending.json')
    legacy = [
        {'id': 41, 'role': 'claude', 'status': 'played', 'agent': 'a1', 'text': 'first'},
        {'id': 42, 'role': 'user', 'status': 'delivered', 'agent': 'a2', 'text': 'second'},
    ]
    history_file.write_text(json.dumps(legacy))
    state = ListenerState()

    daemon._load_history(state)
    daemon._save_history(state)
    restored = ListenerState()
    daemon._load_history(restored)

    assert restored.snapshot_utterances() == legacy
    assert json.loads(history_file.read_text())['conversations'] == {'a1': [legacy[0]], 'a2': [legacy[1]]}
    assert restored.create_utterance('user', 'recording') == 43
